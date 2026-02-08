"use client";

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
} from "react";
import type {
  FlightData,
  HotelData,
  POIData,
  WeatherData,
  TimelineDayData,
  BudgetSummary,
} from "./types";

// Aggregated travel plan state from SSE agent results
export interface TravelPlanState {
  flights: FlightData[];
  hotels: HotelData[];
  pois: POIData[];
  weather: WeatherData[];
  itinerary: TimelineDayData[];
  budget: BudgetSummary | null;
  sessionId: string;
  destination: string;
}

type Action =
  | { type: "ADD_FLIGHTS"; payload: FlightData[] }
  | { type: "ADD_HOTELS"; payload: HotelData[] }
  | { type: "ADD_POIS"; payload: POIData[] }
  | { type: "SET_WEATHER"; payload: WeatherData[] }
  | { type: "SET_ITINERARY"; payload: TimelineDayData[] }
  | { type: "SET_BUDGET"; payload: BudgetSummary }
  | { type: "SET_SESSION"; payload: { sessionId: string; destination?: string } }
  | { type: "RESET" };

const initialState: TravelPlanState = {
  flights: [],
  hotels: [],
  pois: [],
  weather: [],
  itinerary: [],
  budget: null,
  sessionId: "",
  destination: "",
};

function reducer(state: TravelPlanState, action: Action): TravelPlanState {
  switch (action.type) {
    case "ADD_FLIGHTS":
      return { ...state, flights: [...state.flights, ...action.payload] };
    case "ADD_HOTELS":
      return { ...state, hotels: [...state.hotels, ...action.payload] };
    case "ADD_POIS":
      return { ...state, pois: [...state.pois, ...action.payload] };
    case "SET_WEATHER":
      return { ...state, weather: action.payload };
    case "SET_ITINERARY":
      return { ...state, itinerary: action.payload };
    case "SET_BUDGET":
      return { ...state, budget: action.payload };
    case "SET_SESSION":
      return {
        ...state,
        sessionId: action.payload.sessionId,
        destination: action.payload.destination || state.destination,
      };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

interface TravelPlanContextValue {
  state: TravelPlanState;
  dispatch: React.Dispatch<Action>;
  hasData: boolean;
}

const TravelPlanContext = createContext<TravelPlanContextValue | null>(null);

export function TravelPlanProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const hasData =
    state.flights.length > 0 ||
    state.hotels.length > 0 ||
    state.pois.length > 0 ||
    state.weather.length > 0 ||
    state.itinerary.length > 0 ||
    state.budget !== null;

  return (
    <TravelPlanContext.Provider value={{ state, dispatch, hasData }}>
      {children}
    </TravelPlanContext.Provider>
  );
}

export function useTravelPlan(): TravelPlanContextValue {
  const ctx = useContext(TravelPlanContext);
  if (!ctx) {
    throw new Error("useTravelPlan must be used inside TravelPlanProvider");
  }
  return ctx;
}
