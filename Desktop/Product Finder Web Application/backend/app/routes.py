from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mongo
import math
from functools import wraps
from bson import ObjectId
from bson.errors import InvalidId

main = Blueprint('main', __name__)

# =====================================================
# Role Decorators
# =====================================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        identity = get_jwt_identity()
        user = mongo.db.users.find_one({"_id": ObjectId(identity)})
        if not user or user.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def vendor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        identity = get_jwt_identity()
        user = mongo.db.users.find_one({"_id": ObjectId(identity)})
        if not user or user.get('role') not in ['vendor', 'admin']:
            return jsonify({"error": "Vendor access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# Helper Functions
# =====================================================

def validate_pagination(page, per_page):
    """Validate and sanitize pagination parameters"""
    try:
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), 100))  # Cap at 100
    except (ValueError, TypeError):
        page = 1
        per_page = 6
    return page, per_page


def build_product_query(filters):
    """Build MongoDB query from filter parameters"""
    query = {}
    
    if filters.get('brand'):
        query["brand"] = filters['brand']
    
    if filters.get('category'):
        query["category"] = filters['category']
    
    if filters.get('price_max'):
        try:
            price_max = float(filters['price_max'])
            if price_max > 0:
                query["price"] = {"$lte": price_max}
        except (ValueError, TypeError):
            pass
    
    if filters.get('price_min'):
        try:
            price_min = float(filters['price_min'])
            if price_min >= 0:
                if "price" in query:
                    query["price"]["$gte"] = price_min
                else:
                    query["price"] = {"$gte": price_min}
        except (ValueError, TypeError):
            pass
    
    # Specification filters
    spec_filters = ['ram', 'storage']
    for spec in spec_filters:
        if filters.get(spec):
            query[f"specifications.{spec.upper()}"] = filters[spec]

    if filters.get('color'):
        query["specifications.Color"] = filters['color']
    
    if filters.get('vendor_id'):
        try:
            query["vendors.vendor_id"] = ObjectId(filters['vendor_id'])
        except (ValueError, TypeError, InvalidId):
            pass
    
    return query


def serialize_product(product):
    """Convert product document to JSON-serializable format"""
    if product:
        if "_id" in product:
            product["_id"] = str(product["_id"])
        
        # Add vendor_count for the listing page requirement
        if "vendors" in product and isinstance(product["vendors"], list):
            product["vendor_count"] = len(product["vendors"])
            # Also serialize vendor_id in vendors array if present
            for vendor_item in product["vendors"]:
                if "vendor_id" in vendor_item:
                    vendor_item["vendor_id"] = str(vendor_item["vendor_id"])
        else:
            product["vendor_count"] = 0
    
    return product


# =====================================================
# Error Handlers
# =====================================================

@main.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Resource not found"}), 404


@main.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


# =====================================================
# Page Routes
# =====================================================

@main.route('/')
def index():
    """Render the main page"""
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({"error": "Failed to load page", "message": str(e)}), 500


# =====================================================
# API Routes
# =====================================================

@main.route('/api/filters', methods=['GET'])
def get_filters():
    """
    Get all available filter options dynamically from products
    
    Returns:
        JSON with filter options (brands, categories, ram, storage, colors)
    """
    try:
        # Aggregate distinct values efficiently
        pipeline = [
            {
                "$facet": {
                    "brands": [
                        {"$group": {"_id": "$brand"}},
                        {"$sort": {"_id": 1}}
                    ],
                    "categories": [
                        {"$group": {"_id": "$category"}},
                        {"$sort": {"_id": 1}}
                    ],
                    "ram": [
                        {"$group": {"_id": "$specifications.RAM"}},
                        {"$match": {"_id": {"$ne": None}}},
                        {"$sort": {"_id": 1}}
                    ],
                    "storage": [
                        {"$group": {"_id": "$specifications.Storage"}},
                        {"$match": {"_id": {"$ne": None}}},
                        {"$sort": {"_id": 1}}
                    ],
                    "colors": [
                        {"$group": {"_id": "$specifications.Color"}},
                        {"$match": {"_id": {"$ne": None}}},
                        {"$sort": {"_id": 1}}
                    ],
                    "price_range": [
                        {
                            "$group": {
                                "_id": None,
                                "min": {"$min": "$price"},
                                "max": {"$max": "$price"}
                            }
                        }
                    ]
                }
            }
        ]
        
        result = list(mongo.db.products.aggregate(pipeline))
        
        if not result:
            return jsonify({
                "brands": [],
                "categories": [],
                "ram": [],
                "storage": [],
                "colors": [],
                "price_range": {"min": 0, "max": 0}
            })
        
        data = result[0]
        
        # Extract and format data
        filters = {
            "brands": [item["_id"] for item in data.get("brands", []) if item["_id"]],
            "categories": [item["_id"] for item in data.get("categories", []) if item["_id"]],
            "ram": [item["_id"] for item in data.get("ram", []) if item["_id"]],
            "storage": [item["_id"] for item in data.get("storage", []) if item["_id"]],
            "colors": [item["_id"] for item in data.get("colors", []) if item["_id"]],
            "price_range": data.get("price_range", [{}])[0] if data.get("price_range") else {"min": 0, "max": 0}
        }
        
        return jsonify(filters)
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch filters", "message": str(e)}), 500


@main.route('/api/products', methods=['GET'])
@jwt_required()
def get_products():
    """
    Get filtered products with pagination
    
    Query Parameters:
        brand (str): Filter by brand
        category (str): Filter by category
        price_max (float): Maximum price
        price_min (float): Minimum price
        ram (str): Filter by RAM
        storage (str): Filter by storage
        color (str): Filter by color
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 6, max: 100)
        sort (str): Sort field (price, name)
        order (str): Sort order (asc, desc)
    
    Returns:
        JSON with products array and pagination metadata
    """
    try:
        # Get and validate parameters
        page, per_page = validate_pagination(
            request.args.get('page', 1),
            request.args.get('per_page', 6)
        )
        
        # Build query from filters
        filters = {
            'brand': request.args.get('brand'),
            'category': request.args.get('category'),
            'price_max': request.args.get('price_max'),
            'price_min': request.args.get('price_min'),
            'ram': request.args.get('ram'),
            'storage': request.args.get('storage'),
            'color': request.args.get('color'),
            'vendor_id': request.args.get('vendor_id')
        }
        
        query = build_product_query(filters)
        
        # Sorting
        sort_field = request.args.get('sort', 'name')
        sort_order = 1 if request.args.get('order', 'asc') == 'asc' else -1
        
        # Validate sort field
        valid_sort_fields = ['name', 'price', 'brand', 'category']
        if sort_field not in valid_sort_fields:
            sort_field = 'name'
        
        # Count total matching documents
        total = mongo.db.products.count_documents(query)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        
        # Ensure page is within bounds
        page = min(page, total_pages)
        
        # Fetch products
        products_cursor = mongo.db.products.find(query)\
            .sort(sort_field, sort_order)\
            .skip((page - 1) * per_page)\
            .limit(per_page)
        
        products = [serialize_product(p) for p in products_cursor]
        
        response = {
            "products": products,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch products", "message": str(e)}), 500


@main.route('/api/products/<product_id>', methods=['GET'])
def get_product_details(product_id):
    """
    Get product details with vendors
    
    Args:
        product_id (str): MongoDB ObjectId or product name
    
    Returns:
        JSON with complete product details and enriched vendor information
    """
    try:
        # Try to find by ObjectId first
        try:
            product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        except InvalidId:
            # Fallback to name search
            product = mongo.db.products.find_one({"name": product_id})
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Serialize product
        product = serialize_product(product)
        
        # Enrich vendor data
        if "vendors" in product and product["vendors"]:
            enriched_vendors = []
            
            for v in product["vendors"]:
                if "vendor_id" in v:
                    try:
                        vendor = mongo.db.vendors.find_one({"_id": v["vendor_id"]})
                        
                        if vendor:
                            enriched_vendors.append({
                                "vendor_id": str(vendor["_id"]),
                                "vendor_name": vendor.get("name", "Unknown"),
                                "rating": vendor.get("rating", 0),
                                "rating_count": vendor.get("rating_count", "0"),
                                "price": v.get("price", 0),
                                "stock": v.get("stock", 0),
                                "availability": "In Stock" if v.get("stock", 0) > 0 else "Out of Stock"
                            })
                    except Exception as e:
                        # Skip invalid vendor references
                        continue
            
            product["vendors"] = enriched_vendors
            
            # Add price comparison stats
            if enriched_vendors:
                prices = [v["price"] for v in enriched_vendors]
                product["price_stats"] = {
                    "lowest": min(prices),
                    "highest": max(prices),
                    "average": round(sum(prices) / len(prices), 2)
                }
        
        return jsonify(product)
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch product details", "message": str(e)}), 500


# =====================================================
# Additional API Endpoints
# =====================================================

@main.route('/api/products/<product_id>/vendors', methods=['GET'])
def get_product_vendors(product_id):
    """
    Get only vendor information for a specific product
    
    Args:
        product_id (str): MongoDB ObjectId
    
    Returns:
        JSON with vendor list
    """
    try:
        try:
            product = mongo.db.products.find_one(
                {"_id": ObjectId(product_id)},
                {"vendors": 1, "name": 1}
            )
        except InvalidId:
            return jsonify({"error": "Invalid product ID"}), 400
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        enriched_vendors = []
        
        if "vendors" in product and product["vendors"]:
            for v in product["vendors"]:
                if "vendor_id" in v:
                    vendor = mongo.db.vendors.find_one({"_id": v["vendor_id"]})
                    if vendor:
                        enriched_vendors.append({
                            "vendor_name": vendor["name"],
                            "rating": vendor.get("rating"),
                            "price": v["price"],
                            "stock": v["stock"]
                        })
        
        return jsonify({
            "product_name": product.get("name"),
            "vendors": enriched_vendors
        })
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch vendors", "message": str(e)}), 500


@main.route('/api/search', methods=['GET'])
def search_products():
    """
    Search products by name or description
    
    Query Parameters:
        q (str): Search query
        page (int): Page number
        per_page (int): Items per page
    
    Returns:
        JSON with matching products
    """
    try:
        query_text = request.args.get('q', '').strip()
        
        if not query_text:
            return jsonify({"error": "Search query is required"}), 400
        
        page, per_page = validate_pagination(
            request.args.get('page', 1),
            request.args.get('per_page', 6)
        )
        
        # Build text search query
        search_query = {
            "$or": [
                {"name": {"$regex": query_text, "$options": "i"}},
                {"brand": {"$regex": query_text, "$options": "i"}},
                {"category": {"$regex": query_text, "$options": "i"}},
                {"short_description": {"$regex": query_text, "$options": "i"}}
            ]
        }
        
        total = mongo.db.products.count_documents(search_query)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        
        products_cursor = mongo.db.products.find(search_query)\
            .skip((page - 1) * per_page)\
            .limit(per_page)
        
        products = [serialize_product(p) for p in products_cursor]
        
        return jsonify({
            "products": products,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "query": query_text
        })
        
    except Exception as e:
        return jsonify({"error": "Search failed", "message": str(e)}), 500


@main.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get application statistics
    
    Returns:
        JSON with database statistics
    """
    try:
        stats = {
            "total_products": mongo.db.products.count_documents({}),
            "total_vendors": mongo.db.vendors.count_documents({}),
            "categories": mongo.db.products.distinct("category"),
            "brands": mongo.db.products.distinct("brand")
        }
        
        stats["category_count"] = len(stats["categories"])
        stats["brand_count"] = len(stats["brands"])
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": "Failed to fetch stats", "message": str(e)}), 500


@main.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Returns:
        JSON with application health status
    """
    try:
        # Test database connection
        mongo.db.command('ping')
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": mongo.db.command('serverStatus')['localTime']
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 503

# =====================================================
# Management Routes (Admin & Vendor)
# =====================================================

@main.route('/api/admin/users', methods=['GET'])
@jwt_required()
@admin_required
def get_all_users():
    """Admin: Get all registered users"""
    try:
        users = list(mongo.db.users.find({}, {"password": 0}))
        for u in users:
            u['_id'] = str(u['_id'])
            if 'vendor_id' in u:
                u['vendor_id'] = str(u['vendor_id'])
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/admin/users/<user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    """Admin: Delete a user"""
    try:
        # Prevent admin from deleting themselves if they want
        # result = mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        result = mongo.db.users.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count:
            return jsonify({"message": "User deleted"}), 200
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/admin/vendors', methods=['GET'])
@jwt_required()
@admin_required
def get_all_vendors():
    """Admin: Get all vendors"""
    try:
        vendors = list(mongo.db.vendors.find())
        for v in vendors:
            v['_id'] = str(v['_id'])
        return jsonify(vendors)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/admin/vendors/<vendor_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_vendor(vendor_id):
    """Admin: Delete a vendor"""
    try:
        result = mongo.db.vendors.delete_one({"_id": ObjectId(vendor_id)})
        if result.deleted_count:
            return jsonify({"message": "Vendor deleted"}), 200
        return jsonify({"error": "Vendor not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@jwt_required()
@vendor_required
def add_product():
    """Vendor/Admin: Add new product"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        vendor_id = user.get('vendor_id')

        # Ensure name and category are present
        if not data.get('name') or not data.get('category'):
            return jsonify({"error": "Missing name or category"}), 400
            
        new_product = {
            "name": data['name'],
            "brand": data.get('brand', 'Unknown'),
            "category": data['category'],
            "price": float(data.get('price', 0)),
            "short_description": data.get('short_description', ''),
            "full_description": data.get('full_description', ''),
            "specifications": data.get('specifications', {}),
            "vendors": [{
                "vendor_id": ObjectId(vendor_id) if vendor_id else None,
                "price": float(data.get('price', 0)),
                "stock": int(data.get('stock', 0))
            }] if vendor_id else [],
            "vendor_count": 1 if vendor_id else 0
        }
        
        result = mongo.db.products.insert_one(new_product)
        return jsonify({"message": "Product added", "id": str(result.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/products/<product_id>', methods=['DELETE'])
@jwt_required()
@vendor_required
def delete_product(product_id):
    """Vendor/Admin: Delete product"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        query = {"_id": ObjectId(product_id)}
        
        # If not admin, can only delete if it's their product
        if user.get('role') != 'admin':
            vendor_id = user.get('vendor_id')
            if not vendor_id:
                return jsonify({"error": "Vendor profile not found"}), 403
            query["vendors.vendor_id"] = ObjectId(vendor_id)
            
        result = mongo.db.products.delete_one(query)
        if result.deleted_count:
            return jsonify({"message": "Product deleted"}), 200
        return jsonify({"error": "Product not found or unauthorized"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
