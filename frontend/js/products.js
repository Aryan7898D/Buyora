/* ============================================================
   BUYORA — Product Catalog
   Gaming & computer store: laptops, graphics cards, monitors,
   keyboards, mice, headsets, and mouse pads. Prices are in
   Indian Rupees (₹). Product photos live in assets/products/.

   Fields:
   - price / oldPrice : selling price and struck-through price
   - emi              : "or ₹X/month" figure (null to hide)
   - stock            : units available (5 or fewer shows "Low stock")
   - rating / reviews : null / 0 = no reviews yet (stars are hidden)
   ============================================================ */

const PRODUCTS = [
  {
    id: "p01",
    name: "Dell Alienware 15 2026 AMD Gaming Laptop (AMD Ryzen)",
    category: "Laptops",
    price: 170998,
    oldPrice: 315000,
    emi: 15458,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p01.jpg"],
    description: "A 2026 Alienware gaming laptop powered by an AMD Ryzen processor, with a 15.3-inch display running at a smooth 165Hz refresh rate. Built for fast-paced competitive games, streaming, and heavy multitasking, in the signature dark Alienware design.",
    features: ["AMD Ryzen processor", "15.3-inch display with 165Hz refresh rate", "Alienware gaming design with backlit keyboard", "2026 model, brand new"]
  },
  {
    id: "p02",
    name: "Dell Alienware 15 AMD 2026 Gaming Laptop (AMD Ryzen)",
    category: "Laptops",
    price: 158998,
    oldPrice: 255000,
    emi: 14373,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p02.jpg"],
    description: "A more affordable configuration of the 2026 Alienware 15 gaming laptop. Same AMD Ryzen platform and 165Hz high-refresh display, tuned for gamers who want flagship Alienware looks and performance at a lower price.",
    features: ["AMD Ryzen processor", "15.3-inch display with 165Hz refresh rate", "Alienware gaming design", "2026 model, brand new"]
  },
  {
    id: "p03",
    name: "INNO3D GeForce RTX 5070 Ti iCHILL X3 Graphics Card",
    category: "Graphics Cards",
    price: 148499,
    oldPrice: 480000,
    emi: 13424,
    rating: null,
    reviews: 0,
    stock: 4,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p03.jpg"],
    description: "A high-end NVIDIA GeForce RTX 5070 Ti graphics card with INNO3D's iCHILL X3 triple-fan cooler. Made for 4K gaming, ray tracing, and demanding creative workloads, with 16GB of GDDR7 memory. Stock is limited, so order soon.",
    features: ["NVIDIA GeForce RTX 5070 Ti GPU", "16GB GDDR7 memory", "iCHILL X3 triple-fan cooling", "Built for 4K gaming and ray tracing"]
  },
  {
    id: "p04",
    name: "SteelSeries Arctis Nova 1X Wired Gaming Headset",
    category: "Headsets",
    price: 7999,
    oldPrice: 44000,
    emi: 723,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p04.jpg"],
    description: "A lightweight wired gaming headset from SteelSeries with clear, detailed game audio and a comfortable fit for long sessions. Plug it in over 3.5mm and play on console, PC, or mobile with no software needed.",
    features: ["Wired 3.5mm connection", "Clear, balanced gaming audio", "Lightweight, comfortable design for long sessions", "Built-in microphone for voice chat"]
  },
  {
    id: "p05",
    name: "SteelSeries Prime Wired Gaming Mouse (Black)",
    category: "Mice",
    price: 1999,
    oldPrice: 18000,
    emi: 500,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p05.jpg"],
    description: "A lightweight esports-grade wired mouse with a precise optical sensor and a comfortable shape that suits most grip styles. Fast, consistent, and built to take daily competitive play.",
    features: ["Esports-grade optical sensor", "Lightweight wired design", "Durable switches built for heavy use", "Comfortable shape for most grip styles"]
  },
  {
    id: "p06",
    name: "SteelSeries Aerox 3 Wireless Gaming Mouse (Ghost)",
    category: "Mice",
    price: 6299,
    oldPrice: 34000,
    emi: 569,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p06.jpg"],
    description: "An ultra-lightweight wireless gaming mouse in a translucent Ghost finish, with a honeycomb shell and vivid RGB lighting. Connect over 2.4GHz or Bluetooth and keep playing for long stretches between charges.",
    features: ["Ultra-lightweight honeycomb shell", "Wireless: 2.4GHz and Bluetooth", "RGB lighting", "Water and dust resistant design"]
  },
  {
    id: "p07",
    name: "Karnage Sentinel 82 Mechanical Wired RGB Gaming Keyboard",
    category: "Keyboards",
    price: 2899,
    oldPrice: 5400,
    emi: 725,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p07.jpg"],
    description: "A compact 82-key mechanical gaming keyboard with RGB backlighting and a wired USB connection. The tight layout frees up desk space for mouse movement while keeping the keys you need for gaming and work.",
    features: ["Compact 82-key layout", "Mechanical switches", "RGB backlighting", "Wired USB connection"]
  },
  {
    id: "p08",
    name: "Karnage Sentinel Mechanical RGB Gaming Keyboard (White)",
    category: "Keyboards",
    price: 2999,
    oldPrice: 7999,
    emi: 750,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p08.jpg"],
    description: "A compact mechanical RGB gaming keyboard in a white, grey and navy colourway, with a handy multimedia knob in the corner. Satisfying key feel, bright lighting, and a design that looks good on any desk.",
    features: ["Mechanical switches", "RGB backlighting", "Multimedia knob", "Compact layout in white, grey and navy"]
  },
  {
    id: "p09",
    name: "SteelSeries QcK 3XXL Gaming Mouse Pad (Black)",
    category: "Mouse Pads",
    price: 4999,
    oldPrice: 11999,
    emi: 652,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p09.jpg"],
    description: "A huge desk-covering cloth mouse pad from SteelSeries, with a smooth micro-woven surface for precise tracking and a non-slip rubber base. Big enough for your keyboard and mouse together, with room for wide mouse sweeps.",
    features: ["Extra-extra-large desk-covering size", "Micro-woven cloth surface for precise tracking", "Non-slip rubber base", "Room for keyboard and mouse together"]
  },
  {
    id: "p10",
    name: "Samsung LS24D304GAWXXL 24 Inch FHD IPS Monitor",
    category: "Monitors",
    price: 7299,
    oldPrice: 38590,
    emi: null,
    rating: null,
    reviews: 0,
    stock: 25,
    badge: "sale",
    colors: null,
    sizes: null,
    images: ["assets/products/p10.jpg"],
    description: "The Samsung Essential Monitor S3: a 24-inch Full HD IPS display with wide viewing angles and accurate colour. A slim-bezel design and a height-adjustable stand make it a comfortable fit for work, study, and everyday entertainment.",
    features: ["24-inch Full HD (1920×1080) IPS panel", "Wide viewing angles", "Slim-bezel design", "Height-adjustable stand"]
  }
];

const CATEGORIES = [
  { name: "Laptops", icon: "laptop" },
  { name: "Graphics Cards", icon: "gpu" },
  { name: "Monitors", icon: "monitor" },
  { name: "Keyboards", icon: "keyboard" },
  { name: "Mice", icon: "mouse" },
  { name: "Headsets", icon: "headset" },
  { name: "Mouse Pads", icon: "mousepad" }
];

function getProductById(id){
  return PRODUCTS.find(p => p.id === id);
}
