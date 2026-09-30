# React Frontend

## Run

From the project root, start the Python API:

```powershell
uvicorn backend.api:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `http://localhost:8000/api` by default. Override it with `VITE_API_URL` if needed.
