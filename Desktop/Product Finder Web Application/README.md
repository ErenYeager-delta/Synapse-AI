# 🔍 TechNest - High-Performance Multi-User E-commerce Engine

TechNest is a state-of-the-art product discovery and management platform. It features a sophisticated Multi-User architecture with **Role-Based Access Control (RBAC)**, custom **JWT session management**, and a high-availability **NoSQL backend**.

## 🛠 Technology Stack

Our architecture is divided into Macro and Micro layers to ensure both scalability and precision performance.

### 🌐 Macro-Scale (The Foundation)

- **Engine**: **Flask (Python 3.12)**. We chose Flask for its "Micro-kernel" design, allowing us to build a custom-tailored API without the bloat of larger frameworks.
- **Data Vault**: **MongoDB Atlas (Document DB)**. Utilized for its dynamic schema capabilities, enabling us to handle varied product specifications (RAM, Storage, Display Type) in a single unified collection.
- **Frontend Identity**: **Vanilla ES6+ JavaScript**. Pure, framework-less logic for near-instant rendering and direct DOM control.

### 🧪 Micro-Scale (The Precision Tools)

- **Security**: **Bcrypt (Blowfish Hashing)**. Every password is salt-hashed before meeting the database.
- **Session Bridge**: **JWT (JSON Web Tokens)**. Stateless authentication that allows for secure, cross-origin communication between the frontend and API.
- **Data Architect**: **PyMongo / Flask-PyMongo**. Specialized drivers for efficient BSON serialization.
- **Routing Engine**: **Flask Blueprints**. Modularised backend structure for clean separation of Auth and Inventory logic.
- **Style System**: **Custom CSS Flexbox/Grid**. A proprietary design system (no Tailwind) for a unique, premium "Apple-esque" aesthetic.
- **Automation**: **Custom Seeding Engine**. A bespoke Python tool (`seed.py`) that handles many-to-many relationship mapping between 66+ products and 6 independent vendors.

## 👥 Integrated User Ecosystem

The platform is a fully integrated ecosystem where three distinct roles interact:

| Role         | Access Level      | Primary Utility                                                 |
| :----------- | :---------------- | :-------------------------------------------------------------- |
| **Admin**    | **God Mode**      | Manage all users, delete vendors, oversee global product lists. |
| **Vendor**   | **Merchant Mode** | Manage their own inventory, add/delete products, monitor stock. |
| **Customer** | **Consumer Mode** | Search, filter by price/spec, discover best deals.              |

## 🔑 Default Credentials

### Administrative

- **Username**: `admin`
- **Password**: `admin123`

### Vendors (Examples)

- **Usernames**: `amazon`, `bestbuy`, `walmart`, `target`
- **Password**: `vendor123`

## 🚀 Deployment Ready

The project is pre-configured for **Vercel** and **GitHub** deployment.

- `vercel.json`: Handles serverless function routing.
- `api/index.py`: Seamless bridge for Flask on serverless architectures.

---

_Engineered by Antigravity for the modern web._
