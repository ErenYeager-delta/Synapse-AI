from pymongo import MongoClient
import json
import os
import random
import bcrypt
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Connect to MongoDB using the URI from .env
MONGO_URI = os.getenv('MONGO_URI', "mongodb://localhost:27017/product_finder_db")
print(f"Connecting to: {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else MONGO_URI}")

client = MongoClient(MONGO_URI)
# Extract database name from URI or use default
db_name = MONGO_URI.split('/')[-1].split('?')[0] if '/' in MONGO_URI else "product_finder_db"
db = client[db_name]

products_collection = db["products"]
vendors_collection = db["vendors"]

# ==================== DATA ====================

# VENDORS (Now a standalone collection source)
VENDORS_DATA = [
    {"name": "Amazon", "rating": 4.8, "rating_count": "10K+"},
    {"name": "Best Buy", "rating": 4.6, "rating_count": "5K+"},
    {"name": "Walmart", "rating": 4.5, "rating_count": "8K+"},
    {"name": "Target", "rating": 4.4, "rating_count": "3K+"},
    {"name": "B&H Photo", "rating": 4.7, "rating_count": "2K+"},
    {"name": "Newegg", "rating": 4.3, "rating_count": "6K+"},
]

PRODUCTS_DATA = [
    # ==================== SMARTPHONES ====================
    # Apple iPhones
    {"name": "iPhone 14", "brand": "Apple", "category": "Smartphones", "price": 999.99,
     "short_description": "Latest smartphone with A16 chip", "full_description": "The iPhone 14 features the A16 Bionic chip, an improved camera system, and all-day battery life.",
     "specifications": {"RAM": "6GB", "Storage": "128GB", "Color": "Black", "Display": "6.1 inch OLED"}, "vendor_count_target": 4},
    {"name": "iPhone 14 Pro", "brand": "Apple", "category": "Smartphones", "price": 1099.99,
     "short_description": "Pro model with Dynamic Island", "full_description": "iPhone 14 Pro with Dynamic Island, 48MP camera, and ProMotion display.",
     "specifications": {"RAM": "6GB", "Storage": "256GB", "Color": "Purple", "Display": "6.1 inch ProMotion"}, "vendor_count_target": 5},
    {"name": "iPhone 15", "brand": "Apple", "category": "Smartphones", "price": 1199.99,
     "short_description": "Newest iPhone with USB-C", "full_description": "iPhone 15 with USB-C, A17 chip, and improved cameras.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Blue", "Display": "6.1 inch OLED"}, "vendor_count_target": 6},
    {"name": "iPhone 15 Pro Max", "brand": "Apple", "category": "Smartphones", "price": 1499.99,
     "short_description": "Ultimate iPhone experience", "full_description": "The most powerful iPhone ever with titanium design and 5x telephoto.",
     "specifications": {"RAM": "8GB", "Storage": "512GB", "Color": "Titanium", "Display": "6.7 inch ProMotion"}, "vendor_count_target": 5},
    {"name": "iPhone SE 2024", "brand": "Apple", "category": "Smartphones", "price": 429.99,
     "short_description": "Affordable iPhone", "full_description": "Compact iPhone with powerful A15 chip at an affordable price.",
     "specifications": {"RAM": "4GB", "Storage": "64GB", "Color": "Red", "Display": "4.7 inch LCD"}, "vendor_count_target": 4},
    
    # Samsung Galaxy
    {"name": "Samsung Galaxy S23", "brand": "Samsung", "category": "Smartphones", "price": 799.99,
     "short_description": "Android flagship with great camera", "full_description": "Galaxy S23 with Snapdragon 8 Gen 2 and excellent low-light photography.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Green", "Display": "6.1 inch AMOLED"}, "vendor_count_target": 5},
    {"name": "Samsung Galaxy S23 Ultra", "brand": "Samsung", "category": "Smartphones", "price": 1199.99,
     "short_description": "Ultimate Android flagship", "full_description": "200MP camera, S Pen included, and the best Samsung display ever.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Black", "Display": "6.8 inch AMOLED"}, "vendor_count_target": 6},
    {"name": "Samsung Galaxy S24", "brand": "Samsung", "category": "Smartphones", "price": 899.99,
     "short_description": "AI-powered smartphone", "full_description": "Galaxy S24 with Galaxy AI features and improved design.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Violet", "Display": "6.2 inch AMOLED"}, "vendor_count_target": 4},
    {"name": "Samsung Galaxy A54", "brand": "Samsung", "category": "Smartphones", "price": 449.99,
     "short_description": "Mid-range Samsung phone", "full_description": "Great value with flagship features at a mid-range price.",
     "specifications": {"RAM": "6GB", "Storage": "128GB", "Color": "White", "Display": "6.4 inch AMOLED"}, "vendor_count_target": 5},
    {"name": "Samsung Galaxy Z Fold 5", "brand": "Samsung", "category": "Smartphones", "price": 1799.99,
     "short_description": "Foldable phone", "full_description": "The most advanced foldable phone with improved hinge design.",
     "specifications": {"RAM": "12GB", "Storage": "512GB", "Color": "Blue", "Display": "7.6 inch Foldable"}, "vendor_count_target": 3},
    {"name": "Samsung Galaxy Z Flip 5", "brand": "Samsung", "category": "Smartphones", "price": 999.99,
     "short_description": "Compact foldable", "full_description": "Stylish flip phone with larger cover screen.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Purple", "Display": "6.7 inch Foldable"}, "vendor_count_target": 4},
    
    # Google Pixel
    {"name": "Google Pixel 8", "brand": "Google", "category": "Smartphones", "price": 699.99,
     "short_description": "Pure Android experience", "full_description": "Best-in-class camera with Google AI features built in.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Rose", "Display": "6.2 inch OLED"}, "vendor_count_target": 4},
    {"name": "Google Pixel 8 Pro", "brand": "Google", "category": "Smartphones", "price": 999.99,
     "short_description": "Pro camera phone", "full_description": "Professional-grade camera with temperature sensor and AI magic.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Bay", "Display": "6.7 inch LTPO"}, "vendor_count_target": 5},
    {"name": "Google Pixel 7a", "brand": "Google", "category": "Smartphones", "price": 499.99,
     "short_description": "Affordable Pixel", "full_description": "Great camera and software experience at a lower price.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Charcoal", "Display": "6.1 inch OLED"}, "vendor_count_target": 4},
    {"name": "Google Pixel Fold", "brand": "Google", "category": "Smartphones", "price": 1799.99,
     "short_description": "Google's first foldable", "full_description": "Foldable Pixel with incredible camera and large inner display.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Obsidian", "Display": "7.6 inch Foldable"}, "vendor_count_target": 2},
    
    # OnePlus
    {"name": "OnePlus 12", "brand": "OnePlus", "category": "Smartphones", "price": 799.99,
     "short_description": "Flagship killer", "full_description": "Snapdragon 8 Gen 3 with Hasselblad camera system.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Black", "Display": "6.82 inch AMOLED"}, "vendor_count_target": 4},
    {"name": "OnePlus 11", "brand": "OnePlus", "category": "Smartphones", "price": 699.99,
     "short_description": "Previous gen flagship", "full_description": "Still powerful with excellent performance and value.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Green", "Display": "6.7 inch AMOLED"}, "vendor_count_target": 5},
    {"name": "OnePlus Nord 3", "brand": "OnePlus", "category": "Smartphones", "price": 399.99,
     "short_description": "Mid-range champion", "full_description": "Great specs at an unbeatable price point.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Gray", "Display": "6.74 inch AMOLED"}, "vendor_count_target": 3},
    {"name": "OnePlus Open", "brand": "OnePlus", "category": "Smartphones", "price": 1699.99,
     "short_description": "OnePlus foldable", "full_description": "Premium foldable with Hasselblad cameras.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Green", "Display": "7.82 inch Foldable"}, "vendor_count_target": 2},
    
    # Xiaomi
    {"name": "Xiaomi 14", "brand": "Xiaomi", "category": "Smartphones", "price": 899.99,
     "short_description": "Leica camera phone", "full_description": "Flagship with Leica optics and premium build quality.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "White", "Display": "6.36 inch AMOLED"}, "vendor_count_target": 3},
    {"name": "Xiaomi 14 Ultra", "brand": "Xiaomi", "category": "Smartphones", "price": 1199.99,
     "short_description": "Ultimate camera phone", "full_description": "Variable aperture Leica lens with pro photography features.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Black", "Display": "6.73 inch AMOLED"}, "vendor_count_target": 2},
    {"name": "Xiaomi 13T Pro", "brand": "Xiaomi", "category": "Smartphones", "price": 649.99,
     "short_description": "Pro photography", "full_description": "Excellent camera performance with Leica partnership.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Blue", "Display": "6.67 inch AMOLED"}, "vendor_count_target": 4},
    {"name": "Redmi Note 13 Pro", "brand": "Xiaomi", "category": "Smartphones", "price": 299.99,
     "short_description": "Budget king", "full_description": "Incredible value with flagship-like features.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Green", "Display": "6.67 inch AMOLED"}, "vendor_count_target": 5},
    {"name": "POCO F5 Pro", "brand": "Xiaomi", "category": "Smartphones", "price": 449.99,
     "short_description": "Gaming champion", "full_description": "Snapdragon 8+ Gen 1 at an incredible price.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Black", "Display": "6.67 inch AMOLED"}, "vendor_count_target": 3},
    
    # Sony
    {"name": "Sony Xperia 1 V", "brand": "Sony", "category": "Smartphones", "price": 1399.99,
     "short_description": "Creator's phone", "full_description": "4K OLED display with professional camera features.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Black", "Display": "6.5 inch 4K OLED"}, "vendor_count_target": 2},
    {"name": "Sony Xperia 5 V", "brand": "Sony", "category": "Smartphones", "price": 999.99,
     "short_description": "Compact flagship", "full_description": "Compact design with flagship features.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Blue", "Display": "6.1 inch OLED"}, "vendor_count_target": 3},
    
    # Motorola
    {"name": "Motorola Edge 40 Pro", "brand": "Motorola", "category": "Smartphones", "price": 799.99,
     "short_description": "Curved edge display", "full_description": "Stunning curved display with flagship specs.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Black", "Display": "6.67 inch pOLED"}, "vendor_count_target": 3},
    {"name": "Motorola Razr 40 Ultra", "brand": "Motorola", "category": "Smartphones", "price": 1099.99,
     "short_description": "Flip phone reimagined", "full_description": "Large external display on a flip phone.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Black", "Display": "6.9 inch Foldable"}, "vendor_count_target": 2},
    
    # ==================== LAPTOPS ====================
    # Apple MacBooks
    {"name": "MacBook Air M3", "brand": "Apple", "category": "Laptops", "price": 1099.99,
     "short_description": "Thin and light laptop", "full_description": "All-day battery with the new M3 chip.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Silver", "Display": "13.6 inch Retina"}, "vendor_count_target": 5},
    {"name": "MacBook Air 15 M3", "brand": "Apple", "category": "Laptops", "price": 1299.99,
     "short_description": "Larger MacBook Air", "full_description": "15-inch display for more productivity.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Midnight", "Display": "15.3 inch Retina"}, "vendor_count_target": 4},
    {"name": "MacBook Pro 14 M3", "brand": "Apple", "category": "Laptops", "price": 1599.99,
     "short_description": "Pro performance", "full_description": "M3 chip with stunning Liquid Retina XDR display.",
     "specifications": {"RAM": "8GB", "Storage": "512GB", "Color": "Space Gray", "Display": "14.2 inch XDR"}, "vendor_count_target": 4},
    {"name": "MacBook Pro 14 M3 Pro", "brand": "Apple", "category": "Laptops", "price": 1999.99,
     "short_description": "Pro chip for creators", "full_description": "M3 Pro chip for demanding workflows.",
     "specifications": {"RAM": "18GB", "Storage": "512GB", "Color": "Space Black", "Display": "14.2 inch XDR"}, "vendor_count_target": 3},
    {"name": "MacBook Pro 16 M3 Max", "brand": "Apple", "category": "Laptops", "price": 3499.99,
     "short_description": "Ultimate performance", "full_description": "M3 Max for the most demanding professional work.",
     "specifications": {"RAM": "36GB", "Storage": "1TB", "Color": "Space Black", "Display": "16.2 inch XDR"}, "vendor_count_target": 2},
    
    # Dell
    {"name": "Dell XPS 13", "brand": "Dell", "category": "Laptops", "price": 999.99,
     "short_description": "Compact powerhouse", "full_description": "Ultra-portable with InfinityEdge display.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Platinum", "Display": "13.4 inch OLED"}, "vendor_count_target": 4},
    {"name": "Dell XPS 15", "brand": "Dell", "category": "Laptops", "price": 1299.99,
     "short_description": "Premium Windows laptop", "full_description": "Beautiful OLED display with Intel Core i7.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Platinum", "Display": "15.6 inch OLED"}, "vendor_count_target": 5},
    {"name": "Dell XPS 17", "brand": "Dell", "category": "Laptops", "price": 1799.99,
     "short_description": "Large screen productivity", "full_description": "17-inch display for ultimate workspace.",
     "specifications": {"RAM": "32GB", "Storage": "1TB", "Color": "Platinum", "Display": "17 inch UHD+"}, "vendor_count_target": 3},
    {"name": "Dell Inspiron 16", "brand": "Dell", "category": "Laptops", "price": 699.99,
     "short_description": "Everyday laptop", "full_description": "Great performance for everyday tasks.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Silver", "Display": "16 inch FHD+"}, "vendor_count_target": 5},
    
    # HP
    {"name": "HP Spectre x360 14", "brand": "HP", "category": "Laptops", "price": 1499.99,
     "short_description": "2-in-1 convertible", "full_description": "Versatile laptop that converts to a tablet.",
     "specifications": {"RAM": "16GB", "Storage": "1TB", "Color": "Nightfall Black", "Display": "14 inch OLED"}, "vendor_count_target": 3},
    {"name": "HP Envy 16", "brand": "HP", "category": "Laptops", "price": 1199.99,
     "short_description": "Creator laptop", "full_description": "Perfect for content creation and design.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Silver", "Display": "16 inch 4K"}, "vendor_count_target": 4},
    {"name": "HP Pavilion 15", "brand": "HP", "category": "Laptops", "price": 599.99,
     "short_description": "Budget-friendly laptop", "full_description": "Affordable laptop for students and home use.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Silver", "Display": "15.6 inch FHD"}, "vendor_count_target": 5},
    
    # Lenovo
    {"name": "Lenovo ThinkPad X1 Carbon", "brand": "Lenovo", "category": "Laptops", "price": 1799.99,
     "short_description": "Business laptop", "full_description": "Legendary reliability for business professionals.",
     "specifications": {"RAM": "32GB", "Storage": "1TB", "Color": "Black", "Display": "14 inch OLED"}, "vendor_count_target": 4},
    {"name": "Lenovo Yoga 9i", "brand": "Lenovo", "category": "Laptops", "price": 1399.99,
     "short_description": "Premium 2-in-1", "full_description": "Rotating soundbar and OLED display.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Oatmeal", "Display": "14 inch OLED"}, "vendor_count_target": 3},
    {"name": "Lenovo IdeaPad Slim 5", "brand": "Lenovo", "category": "Laptops", "price": 649.99,
     "short_description": "Slim and affordable", "full_description": "Great value in a thin design.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Gray", "Display": "14 inch FHD"}, "vendor_count_target": 4},
    
    # ASUS
    {"name": "ASUS ROG Zephyrus G14", "brand": "ASUS", "category": "Laptops", "price": 1599.99,
     "short_description": "Portable gaming", "full_description": "Powerful gaming in a compact form factor.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Gray", "Display": "14 inch QHD 165Hz"}, "vendor_count_target": 3},
    {"name": "ASUS ROG Strix G16", "brand": "ASUS", "category": "Laptops", "price": 1899.99,
     "short_description": "Gaming beast", "full_description": "RTX 4080 and high refresh rate display.",
     "specifications": {"RAM": "32GB", "Storage": "1TB", "Color": "Black", "Display": "16 inch QHD 240Hz"}, "vendor_count_target": 2},
    {"name": "ASUS ZenBook 14", "brand": "ASUS", "category": "Laptops", "price": 899.99,
     "short_description": "Ultrabook excellence", "full_description": "Beautiful OLED in a thin design.",
     "specifications": {"RAM": "16GB", "Storage": "512GB", "Color": "Blue", "Display": "14 inch OLED"}, "vendor_count_target": 4},
    
    # ==================== TABLETS ====================
    {"name": "iPad Pro 12.9 M4", "brand": "Apple", "category": "Tablets", "price": 1099.99,
     "short_description": "Pro tablet with M4 chip", "full_description": "The ultimate iPad with M4 chip and Tandem OLED display.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Silver", "Display": "12.9 inch OLED"}, "vendor_count_target": 5},
    {"name": "iPad Pro 11 M4", "brand": "Apple", "category": "Tablets", "price": 999.99,
     "short_description": "Compact Pro tablet", "full_description": "M4 power in a more portable size.",
     "specifications": {"RAM": "8GB", "Storage": "256GB", "Color": "Space Gray", "Display": "11 inch OLED"}, "vendor_count_target": 5},
    {"name": "iPad Air M2", "brand": "Apple", "category": "Tablets", "price": 599.99,
     "short_description": "Powerful and portable", "full_description": "M2 chip in a thin and light design.",
     "specifications": {"RAM": "8GB", "Storage": "64GB", "Color": "Blue", "Display": "10.9 inch LCD"}, "vendor_count_target": 6},
    {"name": "iPad 10th Gen", "brand": "Apple", "category": "Tablets", "price": 449.99,
     "short_description": "Essential iPad", "full_description": "Great iPad for everyone.",
     "specifications": {"RAM": "4GB", "Storage": "64GB", "Color": "Pink", "Display": "10.9 inch LCD"}, "vendor_count_target": 5},
    {"name": "Samsung Galaxy Tab S9 Ultra", "brand": "Samsung", "category": "Tablets", "price": 1199.99,
     "short_description": "Android tablet king", "full_description": "14.6-inch display with S Pen included.",
     "specifications": {"RAM": "12GB", "Storage": "256GB", "Color": "Graphite", "Display": "14.6 inch AMOLED"}, "vendor_count_target": 3},
    {"name": "Samsung Galaxy Tab S9", "brand": "Samsung", "category": "Tablets", "price": 849.99,
     "short_description": "Premium Android tablet", "full_description": "Premium Android tablet with S Pen included.",
     "specifications": {"RAM": "8GB", "Storage": "128GB", "Color": "Beige", "Display": "11 inch AMOLED"}, "vendor_count_target": 4},
    
    # ==================== HEADPHONES ====================
    {"name": "AirPods Pro 2", "brand": "Apple", "category": "Headphones", "price": 249.99,
     "short_description": "Active noise cancelling", "full_description": "Best-in-class ANC with Adaptive Audio.",
     "specifications": {"Type": "In-ear", "Battery": "6 hours", "Color": "White"}, "vendor_count_target": 6},
    {"name": "AirPods Max", "brand": "Apple", "category": "Headphones", "price": 549.99,
     "short_description": "Premium over-ear", "full_description": "Stunning audio quality with premium materials.",
     "specifications": {"Type": "Over-ear", "Battery": "20 hours", "Color": "Space Gray"}, "vendor_count_target": 4},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "category": "Headphones", "price": 399.99,
     "short_description": "Best ANC headphones", "full_description": "Industry-leading noise cancellation with 30-hour battery.",
     "specifications": {"Type": "Over-ear", "Battery": "30 hours", "Color": "Black"}, "vendor_count_target": 5},
    {"name": "Sony WF-1000XM5", "brand": "Sony", "category": "Headphones", "price": 299.99,
     "short_description": "Premium earbuds", "full_description": "Compact earbuds with incredible sound.",
     "specifications": {"Type": "In-ear", "Battery": "8 hours", "Color": "Black"}, "vendor_count_target": 4},
    {"name": "Bose QuietComfort Ultra", "brand": "Bose", "category": "Headphones", "price": 429.99,
     "short_description": "Immersive audio", "full_description": "Spatial audio and world-class comfort.",
     "specifications": {"Type": "Over-ear", "Battery": "24 hours", "Color": "Black"}, "vendor_count_target": 4},
    {"name": "Bose QuietComfort Earbuds II", "brand": "Bose", "category": "Headphones", "price": 279.99,
     "short_description": "Best ANC earbuds", "full_description": "CustomTune technology for personalized sound.",
     "specifications": {"Type": "In-ear", "Battery": "6 hours", "Color": "Black"}, "vendor_count_target": 4},
    {"name": "Samsung Galaxy Buds 2 Pro", "brand": "Samsung", "category": "Headphones", "price": 229.99,
     "short_description": "Galaxy earbuds", "full_description": "Hi-Fi sound with intelligent ANC.",
     "specifications": {"Type": "In-ear", "Battery": "5 hours", "Color": "Graphite"}, "vendor_count_target": 5},
    {"name": "Sennheiser Momentum 4", "brand": "Sennheiser", "category": "Headphones", "price": 379.99,
     "short_description": "Audiophile choice", "full_description": "Exceptional sound quality for audiophiles.",
     "specifications": {"Type": "Over-ear", "Battery": "60 hours", "Color": "Black"}, "vendor_count_target": 3},
    
    # ==================== SMARTWATCHES ====================
    {"name": "Apple Watch Ultra 2", "brand": "Apple", "category": "Smartwatches", "price": 799.99,
     "short_description": "Adventure smartwatch", "full_description": "Most rugged Apple Watch with precision GPS.",
     "specifications": {"Display": "49mm", "Battery": "36 hours", "Color": "Titanium"}, "vendor_count_target": 4},
    {"name": "Apple Watch Series 9", "brand": "Apple", "category": "Smartwatches", "price": 399.99,
     "short_description": "Essential smartwatch", "full_description": "Double tap gesture and brighter display.",
     "specifications": {"Display": "45mm", "Battery": "18 hours", "Color": "Pink"}, "vendor_count_target": 5},
    {"name": "Samsung Galaxy Watch 6 Classic", "brand": "Samsung", "category": "Smartwatches", "price": 399.99,
     "short_description": "Classic design", "full_description": "Rotating bezel with advanced health features.",
     "specifications": {"Display": "47mm", "Battery": "40 hours", "Color": "Silver"}, "vendor_count_target": 4},
    {"name": "Samsung Galaxy Watch 6", "brand": "Samsung", "category": "Smartwatches", "price": 329.99,
     "short_description": "Android smartwatch", "full_description": "Advanced health monitoring with Wear OS.",
     "specifications": {"Display": "44mm", "Battery": "30 hours", "Color": "Graphite"}, "vendor_count_target": 5},
    {"name": "Google Pixel Watch 2", "brand": "Google", "category": "Smartwatches", "price": 349.99,
     "short_description": "Google smartwatch", "full_description": "Fitbit health features with Wear OS.",
     "specifications": {"Display": "41mm", "Battery": "24 hours", "Color": "Silver"}, "vendor_count_target": 4},
    {"name": "Garmin Fenix 7", "brand": "Garmin", "category": "Smartwatches", "price": 699.99,
     "short_description": "Outdoor sports watch", "full_description": "Ultimate multisport GPS watch.",
     "specifications": {"Display": "47mm", "Battery": "18 days", "Color": "Black"}, "vendor_count_target": 3},
]

def seed_data():
    # Clear existing data
    products_collection.delete_many({})
    vendors_collection.delete_many({})
    print("Cleared existing products and vendors")
    
    # Create Default Admin
    admin_user = {
        "username": "admin",
        "email": "admin@technest.com",
        "password": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "role": "admin",
        "created_at": datetime.utcnow()
    }
    db.users.delete_many({"username": "admin"})
    db.users.insert_one(admin_user)
    print("Default admin user created: admin / admin123")
    
    # Insert Vendors
    vendor_ids = []
    if VENDORS_DATA:
        result = vendors_collection.insert_many(VENDORS_DATA)
        vendor_ids = result.inserted_ids
        print(f"Inserted {len(vendor_ids)} vendors")
        
        # Create user accounts for these vendors so they can login
        print("Creating authenticated Vendor users...")
        for i, v_id in enumerate(vendor_ids):
            # Sanitize name to create a clean username (lowercase, no spaces, no special chars)
            raw_name = VENDORS_DATA[i]['name']
            clean_name = "".join(e for e in raw_name if e.isalnum()).lower()
            
            vendor_user = {
                "username": clean_name,
                "email": f"{clean_name}@technest.com",
                "password": bcrypt.hashpw("vendor123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                "role": "vendor",
                "vendor_id": v_id,
                "created_at": datetime.utcnow()
            }
            db.users.delete_many({"username": clean_name})
            db.users.insert_one(vendor_user)
        print(f"Created {len(vendor_ids)} vendor user accounts (Password: vendor123)")
    
    # Process and insert products with vendor relations
    products_to_insert = []
    
    for p in PRODUCTS_DATA:
        # Link vendors (Many-to-Many)
        p_vendors = []
        target_count = p.get("vendor_count_target", 3)
        num_vendors = min(target_count, len(vendor_ids))
        
        # Select random vendors
        selected_vendor_indices = random.sample(range(len(vendor_ids)), num_vendors)
        
        for idx in selected_vendor_indices:
            vendor_id = vendor_ids[idx]
            
            # Generate random price variation
            price_variation = random.uniform(0.9, 1.1)
            vendor_price = round(p["price"] * price_variation, 2)
            stock = random.randint(0, 50)
            
            # Link to vendor collection
            p_vendors.append({
                "vendor_id": vendor_id,
                "price": vendor_price,
                "stock": stock
            })
            
        p["vendors"] = p_vendors
        p["vendor_count"] = len(p_vendors) # For easy display on frontend
        
        # Remove helper field
        if "vendor_count_target" in p:
            del p["vendor_count_target"]
            
        products_to_insert.append(p)
    
    # Insert products
    if products_to_insert:
        result = products_collection.insert_many(products_to_insert)
        print(f"Inserted {len(result.inserted_ids)} products")

if __name__ == "__main__":
    seed_data()
