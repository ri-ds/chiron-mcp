import {
  combineReducers,
  configureStore,
  ThunkAction,
  PreloadedState,
  Action,
} from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import cohortReducer from "./cohortSlice";
import criteriaSetReducer from "./criteriaSetSlice";
import tableReducer from "./tableSlice";
import reportsReducer from "./reportsSlice";
import reportReducer from "./reportSlice";
import aggReducer from "./aggregateSlice";

// Create the root reducer independently to obtain the RootState type
const rootReducer = combineReducers({
  auth: authReducer,
  cohort: cohortReducer,
  criteriaSet: criteriaSetReducer,
  table: tableReducer,
  reports: reportsReducer,
  report: reportReducer,
  aggregate: aggReducer,
});

export function setupStore(preloadedState?: PreloadedState<RootState>) {
  return configureStore({
    reducer: rootReducer,
    preloadedState,
  });
}

export type RootState = ReturnType<typeof rootReducer>;
export type AppStore = ReturnType<typeof setupStore>;
export type AppDispatch = AppStore["dispatch"];
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;
