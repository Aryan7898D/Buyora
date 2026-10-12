/* ============================================================
   BUYORA — API Client
   Thin wrapper around fetch() for talking to the backend at
   buyora-backend/. Change API_BASE if you deploy the backend
   somewhere other than localhost:5000.
   ============================================================ */

const API_BASE = (typeof window !== "undefined" && window.BUYORA_API_BASE) || "http://localhost:5000/api";
const AUTH_TOKEN_KEY = "buyora_token_v1";

const Api = {
  getToken(){ return localStorage.getItem(AUTH_TOKEN_KEY); },
  setToken(token){ localStorage.setItem(AUTH_TOKEN_KEY, token); },
  clearToken(){ localStorage.removeItem(AUTH_TOKEN_KEY); },
  isLoggedIn(){ return !!Api.getToken(); },

  async request(path, { method = "GET", body, auth = false } = {}){
    const headers = { "Content-Type": "application/json" };
    if(auth){
      const token = Api.getToken();
      if(token) headers.Authorization = "Bearer " + token;
    }
    let res;
    try{
      res = await fetch(API_BASE + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined
      });
    }catch(networkErr){
      // Backend not running / unreachable — let callers fall back to static data.
      const err = new Error("Could not reach the Buyora API. Is the backend running on " + API_BASE + "?");
      err.isNetworkError = true;
      throw err;
    }
    const data = await res.json().catch(() => ({}));
    if(!res.ok){
      const err = new Error(data.error || `Request failed (${res.status})`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },

  // ---- Auth ----
  register(name, email, password){
    return Api.request("/auth/register", { method: "POST", body: { name, email, password } });
  },
  login(email, password){
    return Api.request("/auth/login", { method: "POST", body: { email, password } });
  },
  me(){
    return Api.request("/auth/me", { auth: true });
  },

  // ---- Products ----
  listProducts(params = {}){
    const qs = new URLSearchParams(Object.entries(params).filter(([,v]) => v !== undefined && v !== null && v !== "")).toString();
    return Api.request("/products" + (qs ? "?" + qs : ""));
  },
  getProduct(id){
    return Api.request("/products/" + encodeURIComponent(id));
  },

  // ---- Orders ----
  createOrder(payload){
    return Api.request("/orders", { method: "POST", body: payload, auth: Api.isLoggedIn() });
  },
  myOrders(){
    return Api.request("/orders/mine", { auth: true });
  }
};
