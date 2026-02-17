import traceback
import json

from .model import get_trained_model

try:
    model, scaler, meta = get_trained_model()
    print('TRAIN_DONE')
    print(json.dumps({k: meta.get(k) for k in ['mae','rmse','r2','mape']}))
except Exception as e:
    print('TRAIN_ERROR')
    traceback.print_exc()
