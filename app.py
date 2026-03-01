from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from main import FIS, optimized_portfolio

app = FastAPI(title="Cashflow")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.post("/getFIS")
async def api_getFIS(request: Request):
    data = await request.json()
    risk_profile = data["risk_profile"]
    portfolio = data["portfolio"]
    return FIS(risk_profile, portfolio)

@app.get("/getOptimizedPortfolio")
async def api_getOptimizedPortfolio(risk_profile: str, budget: float):
    score, portfolio = optimized_portfolio(risk_profile, budget)
    return JSONResponse(content={"score": score, "portfolio": portfolio})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9530)
