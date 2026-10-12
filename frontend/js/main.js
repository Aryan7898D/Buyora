/* ============================================================
   BUYORA — Site-wide Behavior
   Mobile nav drawer, header search, and the reusable product
   card renderer used by home, shop, and related-product blocks.
   ============================================================ */

/* ---------- Live backend integration ----------
   If buyora-backend is running (see /buyora-backend/README.md), this pulls
   the real product catalog from the API and overwrites the in-memory
   PRODUCTS array (same shape) so every page — home, shop, product detail —
   automatically switches from static demo data to live data with zero
   other changes. If the backend isn't reachable, it fails silently and
   the site keeps working off the bundled demo catalog. */
let LIVE_BACKEND_CONNECTED = false;

async function tryLoadLiveProducts(){
  if(typeof Api === "undefined") return false;
  try{
    const { products } = await Api.listProducts({});
    if(Array.isArray(products) && products.length){
      PRODUCTS.length = 0;
      products.forEach(p => PRODUCTS.push(p));
      LIVE_BACKEND_CONNECTED = true;
      return true;
    }
  }catch(e){
    LIVE_BACKEND_CONNECTED = false;
  }
  return false;
}

document.addEventListener("DOMContentLoaded", () => {
  /* Mobile drawer */
  const openBtn = document.querySelector("[data-nav-open]");
  const drawer = document.querySelector("[data-nav-drawer]");
  const closeBtn = document.querySelector("[data-nav-close]");
  if(openBtn && drawer){
    openBtn.addEventListener("click", () => drawer.classList.add("open"));
  }
  if(closeBtn && drawer){
    closeBtn.addEventListener("click", () => drawer.classList.remove("open"));
  }
  if(drawer){
    drawer.addEventListener("click", (e) => {
      if(e.target === drawer) drawer.classList.remove("open");
    });
  }

  /* Header search -> shop page */
  document.querySelectorAll("[data-search-form]").forEach(form => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = form.querySelector("input");
      const q = encodeURIComponent(input.value.trim());
      window.location.href = `shop.html${q ? "?q=" + q : ""}`;
    });
  });

  /* Newsletter forms (front-end only) */
  document.querySelectorAll("[data-newsletter-form]").forEach(form => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      form.querySelector("input").value = "";
      showToast("You're subscribed! Watch your inbox for deals.");
    });
  });
});

/* ---------- Star rating renderer ---------- */
function renderStars(rating){
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

/* ---------- Currency formatting (Indian Rupees) ----------
   Uses Indian digit grouping (e.g. ₹1,38,782) via toLocaleString("en-IN"). */
function formatINR(amount){
  return "₹" + Math.round(amount).toLocaleString("en-IN");
}

/* If a product image URL fails to load, hide the broken image instead of
   showing a broken-image icon — the gradient background behind it still
   looks intentional. */
document.addEventListener("error", (e) => {
  if(e.target && e.target.tagName === "IMG"){
    e.target.style.display = "none";
  }
}, true);

/* ---------- Stock status ---------- */
function isLowStock(p){ return p.stock > 0 && p.stock <= 5; }
function stockLabel(p){
  if(p.stock <= 0) return "Out of stock";
  return isLowStock(p) ? "Low stock" : "In stock";
}

/* ---------- Product card markup (used by home + shop) ---------- */
function productCardHTML(p){
  const badge = p.badge === "sale"
    ? `<span class="badge-sale">Sale</span>`
    : p.badge === "new" ? `<span class="badge-new">New</span>` : "";
  const oldPrice = p.oldPrice ? `<span class="price-old">${formatINR(p.oldPrice)}</span>` : "";
  return `
  <div class="product-card" data-product-id="${p.id}">
    ${badge}
    <a class="product-media" href="product.html?id=${p.id}">
      <img src="${p.images[0]}" alt="${p.name}" loading="lazy">
    </a>
    <div class="quick-add">
      <button class="btn btn-dark btn-block btn-sm" onclick="Cart.add('${p.id}',1); showToast('Added to cart: ${p.name.replace(/'/g, "\\'")}');">Add to cart</button>
    </div>
    <div class="product-body">
      <span class="product-cat">${p.category}</span>
      <h3 class="product-name"><a href="product.html?id=${p.id}">${p.name}</a></h3>
      ${p.reviews > 0 ? `<div class="product-rating"><span class="stars">${renderStars(p.rating)}</span><span>(${p.reviews})</span></div>` : ""}
      <div class="product-price"><span class="price-now">${formatINR(p.price)}</span>${oldPrice}</div>
      ${p.emi ? `<div class="product-emi">or <b>${formatINR(p.emi)}</b>/month</div>` : ""}
      <div class="stock-line ${isLowStock(p) ? "low" : "ok"}"><span class="dot"></span>${stockLabel(p)}</div>
    </div>
  </div>`;
}

function renderProductGrid(container, products){
  if(!container) return;
  if(products.length === 0){
    container.innerHTML = `<p style="grid-column:1/-1;text-align:center;color:var(--slate);padding:40px 0;">No products match your filters yet.</p>`;
    return;
  }
  container.innerHTML = products.map(productCardHTML).join("");
}
