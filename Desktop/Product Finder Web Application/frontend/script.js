/**
 * Product Finder - JavaScript
 * Handles filtering, pagination, and product details
 */

// =====================================================
// Configuration
// =====================================================
const API_BASE_URL = ""; // Use relative path to avoid CORS/Origin mismatches
const PRODUCTS_PER_PAGE = 6;

// =====================================================
// State
// =====================================================
let state = {
  filters: {},
  selectedFilters: {},
  products: [],
  currentPage: 1,
  totalPages: 1,
  token: localStorage.getItem('techNestToken'),
  user: localStorage.getItem('techNestUser'),
  role: localStorage.getItem('techNestRole')
};

// =====================================================
// DOM Elements
// =====================================================
const elements = {
  // Auth elements
  userInfo: document.getElementById("userInfo"),
  welcomeMsg: document.getElementById("welcomeMsg"),
  roleBadge: document.getElementById("roleBadge"),
  logoutBtn: document.getElementById("logoutBtn"),

  // Dashboard elements
  dashboardBtn: document.getElementById("dashboardBtn"),
  managementPane: document.getElementById("managementPane"),
  vendorDashboard: document.getElementById("vendorDashboard"),
  adminDashboard: document.getElementById("adminDashboard"),
  vendorProducts: document.getElementById("vendorProducts"),
  mgmtUsers: document.getElementById("mgmtUsers"),
  dashBackBtn: document.getElementById("dashBackBtn"),
  
  // Modal elements
  addProductModal: document.getElementById("addProductModal"),
  openAddProductModal: document.getElementById("openAddProductModal"),
  closeModal: document.getElementById("closeModal"),
  addProductForm: document.getElementById("addProductForm"),
  
  // Admin Create elements
  addAdminModal: document.getElementById("addAdminModal"),
  openAddAdminModal: document.getElementById("openAddAdminModal"),
  closeAdminModal: document.getElementById("closeAdminModal"),
  addAdminForm: document.getElementById("addAdminForm"),
  usersTableContainer: document.getElementById("usersTableContainer"),

  // Filter dropdowns
  brandFilter: document.getElementById("brandFilter"),
  categoryFilter: document.getElementById("categoryFilter"),
  priceFilter: document.getElementById("priceFilter"),
  ramFilter: document.getElementById("ramFilter"),
  storageFilter: document.getElementById("storageFilter"),
  colorFilter: document.getElementById("colorFilter"),

  // Containers
  filterChips: document.getElementById("filterChips"),
  productsGrid: document.getElementById("productsGrid"),
  pagination: document.getElementById("pagination"),
  loadingText: document.getElementById("loadingText"),

  // Panes
  filtersPane: document.getElementById("filtersPane"),
  productsPane: document.getElementById("productsPane"),
  productDetailsPane: document.getElementById("productDetailsPane"),

  // Details elements
  backBtn: document.getElementById("backBtn"),
  detailProductName: document.getElementById("detailProductName"),
  detailProductDescription: document.getElementById("detailProductDescription"),
  detailSpecs: document.getElementById("detailSpecs"),
  detailVendors: document.getElementById("detailVendors"),
};

// =====================================================
// Initialize
// =====================================================
document.addEventListener("DOMContentLoaded", async function () {
  console.log("Product Finder initialized");

  // Check authentication
  if (!checkAuth()) return;

  // Load filters from API
  await loadFilters();

  // Load products
  await loadProducts();

  // Setup event listeners
  setupEventListeners();
});

function checkAuth() {
  if (!state.token) {
    window.location.href = "login.html";
    return false;
  }

  // Show user info
  elements.userInfo.style.display = "flex";
  elements.welcomeMsg.textContent = `Hello, ${state.user}`;
  elements.roleBadge.textContent = state.role;
  
  if (state.role === 'admin') {
    elements.roleBadge.style.background = '#dc2626'; // Red for admin
    elements.dashboardBtn.style.display = 'block';
  } else if (state.role === 'vendor') {
    elements.roleBadge.style.background = '#16a34a'; // Green for vendor
    elements.dashboardBtn.style.display = 'block';
  }

  return true;
}

function toggleDashboard(show) {
  elements.filtersPane.style.display = show ? "none" : "block";
  elements.productsPane.style.display = show ? "none" : "block";
  elements.productDetailsPane.style.display = "none";
  elements.managementPane.style.display = show ? "block" : "none";

  if (show) {
    if (state.role === 'admin') {
      elements.adminDashboard.style.display = "block";
      elements.vendorDashboard.style.display = "none";
      loadAdminUsers();
    } else {
      elements.adminDashboard.style.display = "none";
      elements.vendorDashboard.style.display = "block";
      loadVendorProducts();
    }
  }
}

async function loadVendorProducts() {
  const vendorId = localStorage.getItem('techNestVendorId');
  if (!vendorId) {
    console.error("No vendor identity found in session");
    return;
  }
  try {
    const response = await fetch(`${API_BASE_URL}/api/products?vendor_id=${vendorId}`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    const data = await response.json();
    renderVendorProducts(data.products);
  } catch (err) { console.error(err); }
}

function renderVendorProducts(products) {
  elements.vendorProducts.innerHTML = products.map(p => `
    <div class="mgmt-card">
      <button class="delete-btn" onclick="deleteProduct('${p._id}')">Delete</button>
      <h4>${p.name}</h4>
      <p>$${p.price}</p>
      <p>Stock: ${p.vendors[0].stock}</p>
    </div>
  `).join('');
}

async function deleteProduct(id) {
  if (!confirm('Are you sure you want to delete this product?')) return;
  try {
    const response = await fetch(`${API_BASE_URL}/api/products/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (response.ok) {
      alert('Product deleted');
      loadVendorProducts();
      loadProducts(); // Refresh main list too
    }
  } catch (err) { console.error(err); }
}

async function handleAddProduct(e) {
  e.preventDefault();
  const productData = {
    name: document.getElementById('newProdName').value,
    brand: document.getElementById('newProdBrand').value,
    category: document.getElementById('newProdCategory').value,
    price: document.getElementById('newProdPrice').value,
    short_description: document.getElementById('newProdShortDesc').value,
    stock: document.getElementById('newProdStock').value
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/products`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.token}`
      },
      body: JSON.stringify(productData)
    });

    if (response.ok) {
      alert('Product added successfully!');
      elements.addProductModal.style.display = "none";
      elements.addProductForm.reset();
      loadVendorProducts();
      loadProducts();
    } else {
      const data = await response.json();
      alert(data.error || 'Failed to add product');
    }
  } catch (err) { console.error(err); }
}

async function handleAddAdmin(e) {
  e.preventDefault();
  const userData = {
    username: document.getElementById('newAdminUser').value,
    email: document.getElementById('newAdminEmail').value,
    password: document.getElementById('newAdminPass').value,
    role: 'admin'
  };

  try {
    const response = await fetch(`http://127.0.0.1:5000/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });

    if (response.ok) {
      alert('Admin account created successfully!');
      elements.addAdminModal.style.display = "none";
      elements.addAdminForm.reset();
      loadAdminUsers();
    } else {
      const data = await response.json();
      alert(data.error || 'Failed to create admin');
    }
  } catch (err) { console.error(err); }
}

async function loadAdminUsers() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/users`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    const users = await response.json();
    elements.usersTableContainer.innerHTML = `
      <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
        <thead>
          <tr style="border-bottom: 2px solid #eee; text-align: left;">
            <th style="padding: 10px;">Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(u => `
            <tr style="border-bottom: 1px solid #eee;">
              <td style="padding: 10px;">${u.username}</td>
              <td>${u.email}</td>
              <td><span class="role-badge" style="background: ${u.role==='admin'?'#dc2626':(u.role==='vendor'?'#16a34a':'#666')}">${u.role}</span></td>
              <td><button class="delete-btn" style="position: static;" onclick="deleteUser('${u._id}')">Delete</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) { console.error(err); }
}

async function deleteUser(id) {
  if (!confirm('Are you sure you want to delete this user?')) return;
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (response.ok) {
      alert('User deleted');
      loadAdminUsers();
    }
  } catch (err) { console.error(err); }
}

async function loadAdminVendors() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/vendors`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    const vendors = await response.json();
    document.getElementById('vendorsTableContainer').innerHTML = `
      <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
        <thead>
          <tr style="border-bottom: 2px solid #eee; text-align: left;">
            <th style="padding: 10px;">Vendor Name</th>
            <th>Email</th>
            <th>Rating</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${vendors.map(v => `
            <tr style="border-bottom: 1px solid #eee;">
              <td style="padding: 10px;">${v.name}</td>
              <td>${v.email || 'N/A'}</td>
              <td>${v.rating} ⭐</td>
              <td><button class="delete-btn" style="position: static;" onclick="deleteVendor('${v._id}')">Remove</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) { console.error(err); }
}

async function deleteVendor(id) {
  if (!confirm('Are you sure you want to remove this vendor?')) return;
  try {
    const response = await fetch(`${API_BASE_URL}/api/admin/vendors/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (response.ok) {
      alert('Vendor removed');
      loadAdminVendors();
    }
  } catch (err) { console.error(err); }
}

async function loadAdminAllProducts() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/products?per_page=100`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    const data = await response.json();
    document.getElementById('adminProductsContainer').innerHTML = data.products.map(p => `
      <div class="mgmt-card">
        <button class="delete-btn" onclick="deleteProduct('${p._id}')">Delete</button>
        <h4>${p.name}</h4>
        <p>${p.brand} | ${p.category}</p>
        <p>$${p.price}</p>
      </div>
    `).join('');
  } catch (err) { console.error(err); }
}

function logout() {
  localStorage.clear();
  window.location.href = "login.html";
}

// =====================================================
// API Functions
// =====================================================

async function loadFilters() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/filters`, {
      headers: {
        'Authorization': `Bearer ${state.token}`
      }
    });
    if (!response.ok) {
      console.error(`Filters fetch failed with status ${response.status}`);
      throw new Error("Failed to fetch filters");
    }

    state.filters = await response.json();
    populateFilterDropdowns();
  } catch (error) {
    console.error("Error loading filters:", error);
  }
}

async function loadProducts() {
  showLoading(true);

  try {
    // Build query string from selected filters
    const params = new URLSearchParams();

    Object.entries(state.selectedFilters).forEach(([key, value]) => {
      if (value) {
        params.append(key, value);
      }
    });

    params.append("page", state.currentPage);
    params.append("per_page", PRODUCTS_PER_PAGE);

    const response = await fetch(`${API_BASE_URL}/api/products?${params}`, {
      headers: {
        'Authorization': `Bearer ${state.token}`
      }
    });
    if (!response.ok) throw new Error("Failed to fetch products");

    const data = await response.json();
    state.products = data.products;
    state.totalPages = data.total_pages;

    renderProducts();
    renderPagination();
  } catch (error) {
    console.error("Error loading products:", error);
    elements.productsGrid.innerHTML =
      '<div class="no-products">Failed to load products. Make sure the backend is running.</div>';
  } finally {
    showLoading(false);
  }
}

async function loadProductDetails(productId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/products/${productId}`, {
      headers: {
        'Authorization': `Bearer ${state.token}`
      }
    });
    if (!response.ok) throw new Error("Failed to fetch product details");

    const product = await response.json();
    showProductDetails(product);
  } catch (error) {
    console.error("Error loading product details:", error);
    alert("Failed to load product details");
  }
}

// =====================================================
// UI Functions
// =====================================================

function populateFilterDropdowns() {
  // Populate Brand
  if (state.filters.brands) {
    state.filters.brands.forEach((brand) => {
      const option = document.createElement("option");
      option.value = brand;
      option.textContent = brand;
      elements.brandFilter.appendChild(option);
    });
  }

  // Populate Category
  if (state.filters.categories) {
    state.filters.categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      elements.categoryFilter.appendChild(option);
    });
  }

  // Populate RAM
  if (state.filters.ram) {
    state.filters.ram.forEach((ram) => {
      const option = document.createElement("option");
      option.value = ram;
      option.textContent = ram;
      elements.ramFilter.appendChild(option);
    });
  }

  // Populate Storage
  if (state.filters.storage) {
    state.filters.storage.forEach((storage) => {
      const option = document.createElement("option");
      option.value = storage;
      option.textContent = storage;
      elements.storageFilter.appendChild(option);
    });
  }

  // Populate Color
  if (state.filters.colors) {
    state.filters.colors.forEach((color) => {
      const option = document.createElement("option");
      option.value = color;
      option.textContent = color;
      elements.colorFilter.appendChild(option);
    });
  }
}

function renderProducts() {
  if (state.products.length === 0) {
    elements.productsGrid.innerHTML =
      '<div class="no-products">No products found.</div>';
    return;
  }

  elements.productsGrid.innerHTML = state.products
    .map((product) => {
      // Build key specs string
      let keySpecs = [];
      if (product.specifications) {
        if (product.specifications.RAM)
          keySpecs.push(`RAM: ${product.specifications.RAM}`);
        if (product.specifications.Storage)
          keySpecs.push(`Storage: ${product.specifications.Storage}`);
        if (product.specifications.Display)
          keySpecs.push(`Display: ${product.specifications.Display}`);
      }
      const specsHtml =
        keySpecs.length > 0
          ? `<p class="product-specs">${keySpecs.join(" | ")}</p>`
          : "";

      return `
            <div class="product-card" onclick="loadProductDetails('${product._id}')">
                <span class="product-category-tag">${product.category}</span>
                <h3>${product.name}</h3>
                <p class="product-brand">Brand: ${product.brand}</p>
                <p class="product-price">Price: $${product.price.toFixed(2)}</p>
                <p class="product-description">${product.short_description}</p>
                ${specsHtml}
                <p class="product-vendors">Vendors: ${product.vendor_count}</p>
            </div>
        `;
    })
    .join("");
}

function renderPagination() {
  if (state.totalPages <= 1) {
    elements.pagination.innerHTML = "";
    return;
  }

  let html = "";

  // Previous button
  html += `<button class="page-btn" onclick="goToPage(${state.currentPage - 1})" ${state.currentPage === 1 ? "disabled" : ""}>&lt; Prev</button>`;

  // Page numbers
  for (let i = 1; i <= state.totalPages; i++) {
    html += `<button class="page-btn ${i === state.currentPage ? "active" : ""}" onclick="goToPage(${i})">${i}</button>`;
  }

  // Next button
  html += `<button class="page-btn" onclick="goToPage(${state.currentPage + 1})" ${state.currentPage === state.totalPages ? "disabled" : ""}>Next &gt;</button>`;

  elements.pagination.innerHTML = html;
}

function renderFilterChips() {
  let html = "";

  Object.entries(state.selectedFilters).forEach(([key, value]) => {
    if (value) {
      const displayKey = key.charAt(0).toUpperCase() + key.slice(1);
      html += `
                <div class="filter-chip">
                    <span>${displayKey}: ${value}</span>
                    <button class="chip-remove" onclick="removeFilter('${key}')">&times;</button>
                </div>
            `;
    }
  });

  elements.filterChips.innerHTML = html;
}

function showProductDetails(product) {
  // Hide listing, show details
  elements.filtersPane.style.display = "none";
  elements.productsPane.style.display = "none";
  elements.productDetailsPane.style.display = "block";

  // Populate details
  elements.detailProductName.textContent = product.name;

  // Add category and brand info (remove existing first to avoid duplication)
  const existingCategoryInfo = document.querySelector(".product-category-info");
  if (existingCategoryInfo) existingCategoryInfo.remove();

  const categoryInfo = document.createElement("p");
  categoryInfo.className = "product-category-info";
  categoryInfo.innerHTML = `<strong>Category:</strong> ${product.category} | <strong>Brand:</strong> ${product.brand}`;
  elements.detailProductName.insertAdjacentElement("afterend", categoryInfo);

  elements.detailProductDescription.textContent = product.full_description;

  // Populate specifications
  let specsHtml = "";
  if (product.specifications) {
    Object.entries(product.specifications).forEach(([key, value]) => {
      specsHtml += `<li>${key}: ${value}</li>`;
    });
  }
  elements.detailSpecs.innerHTML = specsHtml;

  // Populate vendors
  let vendorsHtml = "";
  if (product.vendors) {
    product.vendors.forEach((v) => {
      const stockStatus =
        v.stock > 0 ? `In Stock (${v.stock} available)` : "Out of Stock";
      const stockClass = v.stock > 0 ? "in-stock" : "out-of-stock";
      const vendorName =
        v.vendor_name || (v.vendor ? v.vendor.name : "Unknown Vendor");
      vendorsHtml += `<li class="${stockClass}">${vendorName} - $${v.price.toFixed(2)} (${stockStatus})</li>`;
    });
  }
  elements.detailVendors.innerHTML = vendorsHtml;
}

function hideProductDetails() {
  // Show listing, hide details
  elements.filtersPane.style.display = "block";
  elements.productsPane.style.display = "block";
  elements.productDetailsPane.style.display = "none";
}

function showLoading(show) {
  elements.loadingText.style.display = show ? "inline" : "none";
}

// =====================================================
// Event Handlers
// =====================================================

function setupEventListeners() {
  // Filter change events
  elements.brandFilter.addEventListener("change", () =>
    handleFilterChange("brand", elements.brandFilter.value),
  );
  elements.categoryFilter.addEventListener("change", () =>
    handleFilterChange("category", elements.categoryFilter.value),
  );
  elements.ramFilter.addEventListener("change", () =>
    handleFilterChange("ram", elements.ramFilter.value),
  );
  elements.storageFilter.addEventListener("change", () =>
    handleFilterChange("storage", elements.storageFilter.value),
  );
  elements.colorFilter.addEventListener("change", () =>
    handleFilterChange("color", elements.colorFilter.value),
  );

  // Price filter with debounce
  let priceTimeout;
  elements.priceFilter.addEventListener("input", () => {
    clearTimeout(priceTimeout);
    priceTimeout = setTimeout(() => {
      handleFilterChange("price_max", elements.priceFilter.value);
    }, 500);
  });

  // Back button
  elements.backBtn.addEventListener("click", hideProductDetails);

  // Dashboard button
  elements.dashboardBtn.addEventListener("click", () => toggleDashboard(true));

  // Dashboard back button
  elements.dashBackBtn.addEventListener("click", () => toggleDashboard(false));

  // Modal controls
  elements.openAddProductModal.addEventListener("click", () => elements.addProductModal.style.display = "block");
  elements.closeModal.addEventListener("click", () => elements.addProductModal.style.display = "none");
  
  // Close modal on outside click
  window.addEventListener("click", (e) => {
    if (e.target === elements.addProductModal) elements.addProductModal.style.display = "none";
  });

  // Add Product Form
  elements.addProductForm.addEventListener("submit", handleAddProduct);

  // Tab switching for Admin
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const targetTab = e.target.dataset.tab;
      document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      
      document.getElementById(targetTab).style.display = "block";
      e.target.classList.add("active");

      // Load specific tab data
      if (targetTab === 'mgmtUsers') loadAdminUsers();
      if (targetTab === 'mgmtVendors') loadAdminVendors();
      if (targetTab === 'mgmtProducts') loadAdminAllProducts();
    });
  });

  // Admin Create controls
  elements.openAddAdminModal.addEventListener("click", () => elements.addAdminModal.style.display = "block");
  elements.closeAdminModal.addEventListener("click", () => elements.addAdminModal.style.display = "none");
  elements.addAdminForm.addEventListener("submit", handleAddAdmin);

  // Logout button
  elements.logoutBtn.addEventListener("click", logout);
}

function handleFilterChange(filterName, value) {
  if (value) {
    state.selectedFilters[filterName] = value;
  } else {
    delete state.selectedFilters[filterName];
  }

  state.currentPage = 1; // Reset to first page
  renderFilterChips();
  loadProducts();
}

function removeFilter(filterName) {
  delete state.selectedFilters[filterName];

  // Reset corresponding dropdown
  switch (filterName) {
    case "brand":
      elements.brandFilter.value = "";
      break;
    case "category":
      elements.categoryFilter.value = "";
      break;
    case "ram":
      elements.ramFilter.value = "";
      break;
    case "storage":
      elements.storageFilter.value = "";
      break;
    case "color":
      elements.colorFilter.value = "";
      break;
    case "price_max":
      elements.priceFilter.value = "";
      break;
  }

  state.currentPage = 1;
  renderFilterChips();
  loadProducts();
}

function goToPage(page) {
  if (page < 1 || page > state.totalPages) return;
  state.currentPage = page;
  loadProducts();
}
