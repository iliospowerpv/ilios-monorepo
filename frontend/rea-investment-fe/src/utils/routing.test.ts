import { buildLensRoute, getPickerRoute, getCanonicalRoute } from './routing';

describe('buildLensRoute', () => {
  describe('portfolio scope', () => {
    it('should return portfolio lens route for any module', () => {
      expect(buildLensRoute('finance', 'portfolio')).toBe('/finance/scope/portfolio');
      expect(buildLensRoute('asset-management', 'portfolio')).toBe('/asset-management/scope/portfolio');
      expect(buildLensRoute('due-diligence', 'portfolio')).toBe('/due-diligence/scope/portfolio');
      expect(buildLensRoute('operations-and-maintenance', 'portfolio')).toBe(
        '/operations-and-maintenance/scope/portfolio'
      );
    });
  });

  describe('company scope', () => {
    it('should return company lens route when companyId is provided', () => {
      expect(buildLensRoute('finance', 'company', { companyId: 123 })).toBe('/finance/scope/company/123');
      expect(buildLensRoute('asset-management', 'company', { companyId: 456 })).toBe(
        '/asset-management/scope/company/456'
      );
    });

    it('should return picker route when companyId is missing', () => {
      expect(buildLensRoute('finance', 'company')).toBe('/companies');
      expect(buildLensRoute('finance', 'company', {})).toBe('/companies');
      expect(buildLensRoute('finance', 'company', { companyId: null })).toBe('/companies');
    });
  });

  describe('project scope', () => {
    it('should return project lens route when projectId is provided', () => {
      expect(buildLensRoute('finance', 'project', { projectId: 789 })).toBe('/finance/scope/project/789');
      expect(buildLensRoute('due-diligence', 'project', { projectId: 999 })).toBe('/due-diligence/scope/project/999');
    });

    it('should return filtered projects picker when only companyId is provided', () => {
      expect(buildLensRoute('finance', 'project', { companyId: 123 })).toBe('/projects?companyId=123');
    });

    it('should return projects picker when projectId is missing', () => {
      expect(buildLensRoute('finance', 'project')).toBe('/projects');
      expect(buildLensRoute('finance', 'project', {})).toBe('/projects');
      expect(buildLensRoute('finance', 'project', { projectId: null })).toBe('/projects');
    });
  });
});

describe('getPickerRoute', () => {
  it('should return portfolio route', () => {
    expect(getPickerRoute('portfolio')).toBe('/portfolio');
  });

  it('should return companies picker', () => {
    expect(getPickerRoute('company')).toBe('/companies');
  });

  it('should return projects picker', () => {
    expect(getPickerRoute('project')).toBe('/projects');
  });

  it('should return filtered projects picker when companyId is provided', () => {
    expect(getPickerRoute('project', 123)).toBe('/projects?companyId=123');
  });
});

describe('getCanonicalRoute', () => {
  it('should return portfolio canonical route', () => {
    expect(getCanonicalRoute('portfolio')).toBe('/portfolio');
  });

  it('should return company canonical route with id', () => {
    expect(getCanonicalRoute('company', { companyId: 123 })).toBe('/companies/123');
  });

  it('should return companies picker when no companyId', () => {
    expect(getCanonicalRoute('company')).toBe('/companies');
  });

  it('should return project canonical route with id', () => {
    expect(getCanonicalRoute('project', { projectId: 456 })).toBe('/projects/456');
  });

  it('should return projects picker when no projectId', () => {
    expect(getCanonicalRoute('project')).toBe('/projects');
  });
});
