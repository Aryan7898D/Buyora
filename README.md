# Buyora - Gaming & PC Store (Python backend)

Ek hi folder, ek hi command. Python server website bhi dikhata hai aur API bhi deta hai.

```
buyora-python/
├── run.py              <- ye chalao (website + API)
├── manage.py           <- admin password badalna, stats dekhna
├── requirements.txt    <- Flask + MySQL connector
├── app/                <- backend ka code
│   ├── __init__.py       server banana, CORS, errors
│   ├── db.py             MySQL database + pehli baar products load karna
│   ├── auth.py           login token, admin check
│   ├── products.json     product catalog (frontend ke products.js jaisa)
│   └── routes/           auth_routes.py, products_routes.py, orders_routes.py
├── frontend/           <- website (HTML/CSS/JS)
├── tests/              <- API tests (test-only SQLite database)
└── data/               <- secret key; MySQL database server par rehta hai
```

## Chalane ke steps (Windows)

Python 3.9 ya naya chahiye. Check karo: `python --version` (agar nahi chale to `py --version`).

1. VS Code mein is folder ko kholo, Terminal kholo (Ctrl + `)
2. MySQL Server install aur start karo.
3. Python dependencies install karo:
   ```
   pip install -r requirements.txt
   ```
4. Database aur dedicated app account setup karne ke liye chalao:
   ```
   python setup_mysql.py
   ```
   Admin username/password aapse terminal mein poocha jayega; password type
   karte waqt dikhai nahi dega. Script database, app user aur local settings
   banata hai. Settings `data/mysql-config.json` mein rehti hain aur Git mein
   commit nahi hoti. Admin login ke paas database/user create karne ki permission
   honi chahiye. `python run.py --reset` ke liye app user ko DROP permission hai.
5. Server chalao:
   ```
   python run.py
   ```
6. Browser mein kholo: **http://localhost:5000**

Bas. Terminal khula rehna chahiye. Band karne ke liye `Ctrl + C`.

Pehli run par MySQL `buyora` database mein tables banenge; 10 products load honge
aur admin account banega.
Signup, login, cart ke baad order, sab database mein save hota hai aur server band karne ke baad bhi rehta hai.

Purane SQLite database ka data automatic import nahi hota. Agar usmein zaroori
data hai, switch karne se pehle export/import migration karni hogi.

## Vercel deployment

The Flask app can be deployed to Vercel with the root `index.py` entry point.
The Vercel build copies `frontend/` to `public/` so its HTML assets are served
as static files, while `/api/*` is handled by Flask. Vercel must use an
internet-reachable MySQL database; the local `data/mysql-config.json` is not
used there.

1. Import `Aryan7898D/Buyora` as a project in Vercel, with the repository root
   as the Root Directory.
2. In **Project Settings → Environment Variables**, add:
   - `BUYORA_DB_HOST`: the Railway public TCP host (for example,
     `hayabusa.proxy.rlwy.net`; use your own value from Railway)
   - `BUYORA_DB_PORT`: the Railway public TCP port (for example, `48430`)
   - `BUYORA_DB_USER`: Railway's `MYSQLUSER`
   - `BUYORA_DB_PASSWORD`: Railway's `MYSQLPASSWORD`
   - `BUYORA_DB_NAME`: Railway's `MYSQL_DATABASE` or `MYSQLDATABASE`
   - `BUYORA_SECRET_KEY`: a long, randomly generated secret
   - `BUYORA_ADMIN_PASSWORD`: a new, strong initial Buyora admin password
   - `BUYORA_CORS_ORIGIN`: the deployed site's origin, if using a separate
     frontend domain; otherwise the default is `*`
3. Deploy. On first startup, Buyora creates its tables and seeds the products
   and admin account in the Railway database.
4. Open `/api/health` and `/api/products` on the Vercel deployment to verify
   the API and database-backed catalog.

Never put database passwords or the secret key in source control or share them
in screenshots. Set Vercel environment variables for Production and Preview
only as appropriate. Protect the Railway public database with its own strong
password and do not expose its credentials.

## Admin

- Email: `admin@buyora.com`, password: `admin123`
- **Pehle password badal do:** `python manage.py admin-password`
- Admin ke liye abhi screen nahi hai, wo API se hota hai (neeche examples).

## Kaam ki commands

| Kya karna hai | Command |
|---|---|
| Doosre port par chalana | `python run.py --port 5001` |
| Sab kuch naye sire se (products, users, orders mita do) | `python run.py --reset` |
| Phone/doosre device se kholna (same WiFi) | `python run.py --host 0.0.0.0` |
| Kitne products/users/orders hain | `python manage.py stats` |
| Saare tests chalana | `python -m unittest -v` |

## API

Sab JSON hai. Login wale routes ke liye header: `Authorization: Bearer <token>`.

| Method | Path | Kaun | Kya karta hai |
|---|---|---|---|
| GET | `/api/health` | sab | server chal raha hai ya nahi |
| POST | `/api/auth/register` | sab | `{name, email, password}` -> `{token, user}` |
| POST | `/api/auth/login` | sab | `{email, password}` -> `{token, user}` |
| GET | `/api/auth/me` | login | apni details |
| GET | `/api/products` | sab | list; `?category= &minPrice= &maxPrice= &q= &sort=` (sort: `price-asc`, `price-desc`, `name`, `discount`) |
| GET | `/api/products/categories` | sab | categories ki list |
| GET | `/api/products/<id>` | sab | ek product |
| POST / PUT / DELETE | `/api/products[/<id>]` | admin | product add / badlo / hatao |
| POST | `/api/orders` | sab (guest bhi) | order lagana |
| GET | `/api/orders/mine` | login | apne orders |
| GET | `/api/orders/<id>` | owner ya admin | ek order |
| GET | `/api/orders/all` | admin | saare orders |
| PATCH | `/api/orders/<id>/status` | admin | `pending / paid / fulfilled / cancelled` |

**Order kaise safe hai:** browser sirf product id aur quantity bhejta hai. Price, stock check, discount, shipping aur GST server database se khud nikaalta hai. Stock order ke saath hi ghat jata hai, aur do log ek saath aakhri piece nahi kharid sakte.

Store ke rules `app/routes/orders_routes.py` ke upar hain: shipping Rs 99 (Rs 1,999 ya zyada ke cart par free), GST 18%, coupon `WELCOME20` = 20% off.

### Admin se product badalne ka example (PowerShell)

```powershell
$t = (Invoke-RestMethod -Method Post http://localhost:5000/api/auth/login -ContentType application/json `
      -Body '{"email":"admin@buyora.com","password":"APNA_PASSWORD"}').token
# price aur stock badlo
Invoke-RestMethod -Method Put http://localhost:5000/api/products/p10 -Headers @{Authorization="Bearer $t"} `
      -ContentType application/json -Body '{"price": 6999, "stock": 12}'
# saare orders dekho
(Invoke-RestMethod http://localhost:5000/api/orders/all -Headers @{Authorization="Bearer $t"}).orders
```

## Problems

- **`python` command nahi mila:** `py run.py` try karo, ya python.org se Python install karo (install karte waqt "Add Python to PATH" tick karo).
- **Port busy hai:** `python run.py --port 5001`.
- **Naye products dikh nahi rahe:** products database mein pehli run par load hote hain. Catalog badalne ke baad `python run.py --reset` chalao, ya admin API se badlo.
- **Frontend ko Live Server se kholna ho:** `frontend/js/config.js` mein API `http://localhost:5000/api` set hai, bas `python run.py` bhi saath chalta rahe.

## Live (internet par) daalne se pehle

- Admin password badlo, aur `BUYORA_SECRET_KEY` environment variable set karo (nahi to server `data/secret.key` mein ek key khud bana leta hai, use private rakho).
- MySQL ke liye dedicated user/password use karo; `BUYORA_DB_PASSWORD` ko environment variable mein set karo.
- `python run.py` Flask ka development server hai. Live ke liye `waitress` ya `gunicorn` use karo, aur HTTPS lagao.
- `BUYORA_CORS_ORIGIN` ko apni site ke address par set karo (default `*` sab ko allow karta hai).
- Real card payment (Razorpay/Stripe) abhi nahi hai: checkout order save karta hai, paise nahi kaatta.
