/* ============================================================
   BUYORA — Cart Module
   Handles all cart state (persisted to localStorage) and the
   small header cart-count badge shared by every page.
   ============================================================ */

const CART_KEY = "buyora_cart_v1";

const Cart = {
  read(){
    try{
      const raw = localStorage.getItem(CART_KEY);
      return raw ? JSON.parse(raw) : [];
    }catch(e){
      console.error("Cart read failed", e);
      return [];
    }
  },

  write(items){
    try{
      localStorage.setItem(CART_KEY, JSON.stringify(items));
      Cart.updateBadge();
    }catch(e){
      console.error("Cart write failed", e);
    }
  },

  add(productId, qty = 1, options = {}){
    const items = Cart.read();
    const key = productId + "|" + (options.color || "") + "|" + (options.size || "");
    const existing = items.find(i => i.key === key);
    if(existing){
      existing.qty += qty;
    }else{
      items.push({ key, productId, qty, color: options.color || null, size: options.size || null });
    }
    Cart.write(items);
  },

  updateQty(key, qty){
    let items = Cart.read();
    if(qty <= 0){
      items = items.filter(i => i.key !== key);
    }else{
      const it = items.find(i => i.key === key);
      if(it) it.qty = qty;
    }
    Cart.write(items);
  },

  remove(key){
    const items = Cart.read().filter(i => i.key !== key);
    Cart.write(items);
  },

  clear(){
    Cart.write([]);
  },

  count(){
    return Cart.read().reduce((sum, i) => sum + i.qty, 0);
  },

  lines(){
    return Cart.read().map(item => {
      const product = typeof getProductById === "function" ? getProductById(item.productId) : null;
      return { ...item, product };
    }).filter(l => l.product);
  },

  subtotal(){
    return Cart.lines().reduce((sum, l) => sum + l.product.price * l.qty, 0);
  },

  updateBadge(){
    document.querySelectorAll("[data-cart-count]").forEach(el => {
      const n = Cart.count();
      el.textContent = n;
      el.style.display = n > 0 ? "flex" : "none";
    });
  }
};

document.addEventListener("DOMContentLoaded", Cart.updateBadge);

/* ---------- Shared toast ---------- */
function showToast(message, icon = "check"){
  let toast = document.querySelector(".toast");
  if(!toast){
    toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<span class="icon-circle" data-toast-icon></span><span data-toast-text></span>`;
    document.body.appendChild(toast);
  }
  toast.querySelector("[data-toast-text]").textContent = message;
  const iconSvg = icon === "check"
    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>'
    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
  toast.querySelector("[data-toast-icon]").innerHTML = iconSvg;
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), 2600);
}
