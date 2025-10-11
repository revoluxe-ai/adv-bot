from app.modules.grpcs.predict_ctr_service.predict_ctr_service import PredictCTRService


async def run_fit_model_new_test():
    service = PredictCTRService()
    await service._update_model_loop()
    print("Model fitting test completed.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_fit_model_new_test())
