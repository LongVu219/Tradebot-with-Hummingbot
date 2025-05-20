#!/usr/bin/env python3
# Import adapter first to patch MQTT client
import prediction_service_adapter
print("Adapter loaded and MQTT client patched")

# Now run the prediction service
import prediction_service
import asyncio

if __name__ == "__main__":
    print("Starting prediction service with patched MQTT client")
    asyncio.run(prediction_service.main())
