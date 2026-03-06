import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```
Et `index.html` pointe sur `/src/main.jsx`.

---

## Structure cible propre
```
euromillions-grid-generator/
├── backend/
│   ├── app/
│   │   ├── core/config.py
│   │   ├── data/
│   │   │   ├── euromillions_history.csv
│   │   │   └── manifest.json          ← à créer
│   │   ├── models/schemas.py
│   │   ├── routers/{health,models_router,draws,generate}.py
│   │   ├── services/{oracle_stats,smart_grid,data_loader,draw_calendar,generation_service}.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/...
│   │   └── integration/...
│   ├── Dockerfile
│   ├── pytest.ini
│   └── requirements.txt
│                                      ← pytest_stub.py supprimé
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    ← renommé (double extension supprimée)
│   │   └── main.jsx                  ← à créer
│   ├── index.html                    ← à créer
│   ├── vite.config.js                ← à créer
│   ├── package.json                  ← à créer
│   └── Dockerfile                    ← à créer
├── docker-compose.yml                ← déplacé depuis backend/
├── .gitignore
├── LICENSE
└── README.md
