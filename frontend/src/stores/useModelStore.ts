import { create } from 'zustand';
import { ModelInfo, DriftMetric, RegimeStatus, OptunaTrial } from '../types/model';
import {
  QUANT_MODELS,
  INITIAL_REGIME,
  INITIAL_DRIFT,
  INITIAL_OPTUNA_TRIALS,
} from '../lib/mock/quantData';

interface ModelState {
  models: ModelInfo[];
  regime: RegimeStatus;
  driftMetrics: DriftMetric[];
  optunaTrials: OptunaTrial[];
  selectedModelId: string | null;
  setSelectedModelId: (id: string | null) => void;
  promoteChallenger: (challengerId: string) => void;
  updateModelWeight: (id: string, newWeight: number) => void;
}

export const useModelStore = create<ModelState>((set) => ({
  models: [...QUANT_MODELS],
  regime: { ...INITIAL_REGIME },
  driftMetrics: [...INITIAL_DRIFT],
  optunaTrials: [...INITIAL_OPTUNA_TRIALS],
  selectedModelId: QUANT_MODELS[0].id,

  setSelectedModelId: (id) => set({ selectedModelId: id }),

  promoteChallenger: (challengerId) => {
    set((state) => ({
      models: state.models.map((m) => {
        if (m.id === challengerId) {
          return { ...m, champion: true, status: 'CHAMPION' };
        }
        if (m.champion && m.id !== challengerId) {
          return { ...m, champion: false, status: 'CHALLENGER' };
        }
        return m;
      }),
    }));
  },

  updateModelWeight: (id, newWeight) => {
    set((state) => ({
      models: state.models.map((m) => (m.id === id ? { ...m, weight: newWeight } : m)),
    }));
  },
}));
