import Sites from './Sites';
import { createDueDiligenceHandle } from './handle';
import { createDiligenceCompanyDetailsLoader } from './loader';

export default {
  Component: Sites,
  createHandle: createDueDiligenceHandle,
  createLoader: createDiligenceCompanyDetailsLoader
};
