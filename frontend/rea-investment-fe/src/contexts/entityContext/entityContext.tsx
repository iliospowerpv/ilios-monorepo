import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export type EntityLevel = 'portfolio' | 'company' | 'project';
export type ScopeType = 'portfolio' | 'company' | 'project';

export interface EntityInfo {
  id: number;
  name: string;
}

export type ModuleType =
  | 'asset-management'
  | 'operations-and-maintenance'
  | 'due-diligence'
  | 'finance'
  | 'sales'
  | 'reports'
  | 'dashboard'
  | 'my-portfolio'
  | null;

interface EntityContextType {
  currentLevel: EntityLevel;
  currentScope: ScopeType;
  currentCompany: EntityInfo | null;
  currentProject: EntityInfo | null;
  currentModule: ModuleType;
  setCurrentCompany: (company: EntityInfo | null) => void;
  setCurrentProject: (project: EntityInfo | null) => void;
  setCurrentModule: (module: ModuleType) => void;
  setCurrentScope: (scope: ScopeType) => void;
  navigateToLevel: (level: EntityLevel) => void;
  navigateToScope: (scope: ScopeType, options?: { stayInModule?: boolean }) => void;
  navigateToCompany: (company: EntityInfo, options?: { stayInModule?: boolean }) => void;
  navigateToProject: (project: EntityInfo, options?: { stayInModule?: boolean }) => void;
  getModuleBasePath: (module: string) => string;
  getCanonicalPath: (scope: ScopeType) => string;
  getModuleScopedPath: (module: string, scope: ScopeType) => string;
}

const EntityContext = createContext<EntityContextType | undefined>(undefined);

const STORAGE_KEY = 'ilios_entity_context';

interface StoredContext {
  company: EntityInfo | null;
  project: EntityInfo | null;
  scope: ScopeType;
}

const loadStoredContext = (): StoredContext => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        company: parsed.company || null,
        project: parsed.project || null,
        scope: parsed.scope || 'portfolio'
      };
    }
  } catch {
    // ignore
  }
  return { company: null, project: null, scope: 'portfolio' };
};

const saveContext = (context: StoredContext): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
  } catch {
    // ignore
  }
};

export const EntityContextProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const storedContext = loadStoredContext();
  const [currentCompany, setCurrentCompanyState] = useState<EntityInfo | null>(storedContext.company);
  const [currentProject, setCurrentProjectState] = useState<EntityInfo | null>(storedContext.project);
  const [currentScope, setCurrentScopeState] = useState<ScopeType>(storedContext.scope);
  const [currentModule, setCurrentModule] = useState<ModuleType>(null);

  const currentLevel = useMemo((): EntityLevel => {
    const path = location.pathname;
    if (
      path.includes('/scope/project/') ||
      path.includes('/sites/') ||
      path.includes('/projects/') ||
      path.match(/\/project\/\d+/)
    ) {
      return 'project';
    }
    if (path.includes('/scope/company/') || path.includes('/companies/') || path.match(/\/company\/\d+/)) {
      return 'company';
    }
    if (path.includes('/scope/portfolio')) {
      return 'portfolio';
    }
    return 'portfolio';
  }, [location.pathname]);

  useEffect(() => {
    const path = location.pathname;
    if (path.startsWith('/asset-management')) {
      setCurrentModule('asset-management');
    } else if (path.startsWith('/operations-and-maintenance')) {
      setCurrentModule('operations-and-maintenance');
    } else if (path.startsWith('/due-diligence')) {
      setCurrentModule('due-diligence');
    } else if (path.startsWith('/finance')) {
      setCurrentModule('finance');
    } else if (path.startsWith('/sales')) {
      setCurrentModule('sales');
    } else if (path.startsWith('/reports')) {
      setCurrentModule('reports');
    } else if (path.startsWith('/dashboard')) {
      setCurrentModule('dashboard');
    } else if (path.startsWith('/my-portfolio')) {
      setCurrentModule('my-portfolio');
    } else if (path.startsWith('/portfolio') || path.startsWith('/companies') || path.startsWith('/projects')) {
      setCurrentModule(null);
    } else {
      setCurrentModule(null);
    }
  }, [location.pathname]);

  useEffect(() => {
    const path = location.pathname;

    if (path.includes('/scope/project/')) {
      const projectMatch = path.match(/\/scope\/project\/(\d+)/);
      if (projectMatch) {
        setCurrentScopeState('project');
      }
    } else if (path.includes('/scope/company/')) {
      const companyMatch = path.match(/\/scope\/company\/(\d+)/);
      if (companyMatch) {
        setCurrentScopeState('company');
      }
    } else if (path.includes('/scope/portfolio')) {
      setCurrentScopeState('portfolio');
    } else if (path.includes('/project/') || path.includes('/sites/') || path.includes('/projects/')) {
      const projectMatch = path.match(/\/(?:project|sites|projects)\/(\d+)/);
      if (projectMatch) {
        setCurrentScopeState('project');
      }
    } else if (path.includes('/company/') || path.includes('/companies/')) {
      const companyMatch = path.match(/\/(?:company|companies)\/(\d+)/);
      if (companyMatch) {
        setCurrentScopeState('company');
      }
    } else if (path.startsWith('/portfolio') || path.includes('/portfolio')) {
      setCurrentScopeState('portfolio');
    }
  }, [location.pathname]);

  const setCurrentCompany = useCallback(
    (company: EntityInfo | null) => {
      setCurrentCompanyState(company);
      if (!company) {
        setCurrentProjectState(null);
        saveContext({ company: null, project: null, scope: currentScope });
      } else {
        saveContext({ company, project: currentProject, scope: currentScope });
      }
    },
    [currentProject, currentScope]
  );

  const setCurrentProject = useCallback(
    (project: EntityInfo | null) => {
      setCurrentProjectState(project);
      saveContext({ company: currentCompany, project, scope: currentScope });
    },
    [currentCompany, currentScope]
  );

  const setCurrentScope = useCallback(
    (scope: ScopeType) => {
      setCurrentScopeState(scope);
      saveContext({ company: currentCompany, project: currentProject, scope });
    },
    [currentCompany, currentProject]
  );

  const getModuleBasePath = useCallback((module: string): string => {
    switch (module) {
      case 'asset-management':
        return '/asset-management';
      case 'operations-and-maintenance':
        return '/operations-and-maintenance';
      case 'due-diligence':
        return '/due-diligence';
      case 'finance':
        return '/finance';
      case 'sales':
        return '/sales';
      case 'reports':
        return '/reports';
      case 'dashboard':
        return '/dashboard';
      case 'my-portfolio':
        return '/my-portfolio';
      default:
        return '/my-portfolio';
    }
  }, []);

  const getCanonicalPath = useCallback(
    (scope: ScopeType): string => {
      switch (scope) {
        case 'portfolio':
          return '/portfolio';
        case 'company':
          if (currentCompany) {
            return `/companies/${currentCompany.id}`;
          }
          return '/companies';
        case 'project':
          if (currentProject) {
            return `/projects/${currentProject.id}`;
          }
          return '/projects';
      }
    },
    [currentCompany, currentProject]
  );

  const getModuleScopedPath = useCallback(
    (module: string, scope: ScopeType): string => {
      const basePath = getModuleBasePath(module);

      switch (scope) {
        case 'portfolio':
          return `${basePath}/scope/portfolio`;
        case 'company':
          if (currentCompany) {
            return `${basePath}/scope/company/${currentCompany.id}`;
          }
          return '/companies';
        case 'project':
          if (currentProject) {
            return `${basePath}/scope/project/${currentProject.id}`;
          }
          if (currentCompany) {
            return `/projects?companyId=${currentCompany.id}`;
          }
          return '/projects';
      }
    },
    [currentCompany, currentProject, getModuleBasePath]
  );

  const navigateToScope = useCallback(
    (scope: ScopeType, options?: { stayInModule?: boolean }) => {
      const stayInModule = options?.stayInModule ?? true;

      setCurrentScopeState(scope);
      saveContext({ company: currentCompany, project: currentProject, scope });

      if (stayInModule && currentModule) {
        const path = getModuleScopedPath(currentModule, scope);
        navigate(path);
      } else {
        const path = getCanonicalPath(scope);
        navigate(path);
      }
    },
    [currentModule, currentCompany, currentProject, navigate, getModuleScopedPath, getCanonicalPath]
  );

  const navigateToCompany = useCallback(
    (company: EntityInfo, options?: { stayInModule?: boolean }) => {
      const stayInModule = options?.stayInModule ?? true;

      setCurrentCompanyState(company);
      setCurrentScopeState('company');
      saveContext({ company, project: currentProject, scope: 'company' });

      if (stayInModule && currentModule) {
        const basePath = getModuleBasePath(currentModule);
        navigate(`${basePath}/scope/company/${company.id}`);
      } else {
        navigate(`/companies/${company.id}`);
      }
    },
    [currentModule, currentProject, navigate, getModuleBasePath]
  );

  const navigateToProject = useCallback(
    (project: EntityInfo, options?: { stayInModule?: boolean }) => {
      const stayInModule = options?.stayInModule ?? true;

      setCurrentProjectState(project);
      setCurrentScopeState('project');
      saveContext({ company: currentCompany, project, scope: 'project' });

      if (stayInModule && currentModule) {
        const basePath = getModuleBasePath(currentModule);
        navigate(`${basePath}/scope/project/${project.id}`);
      } else {
        navigate(`/projects/${project.id}`);
      }
    },
    [currentModule, currentCompany, navigate, getModuleBasePath]
  );

  const navigateToLevel = useCallback(
    (level: EntityLevel) => {
      const module = currentModule || 'asset-management';
      const basePath = getModuleBasePath(module);

      switch (level) {
        case 'portfolio':
          navigate(`${basePath}/scope/portfolio`);
          break;
        case 'company':
          if (currentCompany) {
            navigate(`${basePath}/scope/company/${currentCompany.id}`);
          } else {
            navigate('/companies');
          }
          break;
        case 'project':
          if (currentProject) {
            navigate(`${basePath}/scope/project/${currentProject.id}`);
          } else if (currentCompany) {
            navigate(`/projects?companyId=${currentCompany.id}`);
          } else {
            navigate('/projects');
          }
          break;
      }
    },
    [currentModule, currentCompany, currentProject, navigate, getModuleBasePath]
  );

  const value = useMemo(
    () => ({
      currentLevel,
      currentScope,
      currentCompany,
      currentProject,
      currentModule,
      setCurrentCompany,
      setCurrentProject,
      setCurrentModule,
      setCurrentScope,
      navigateToLevel,
      navigateToScope,
      navigateToCompany,
      navigateToProject,
      getModuleBasePath,
      getCanonicalPath,
      getModuleScopedPath
    }),
    [
      currentLevel,
      currentScope,
      currentCompany,
      currentProject,
      currentModule,
      setCurrentCompany,
      setCurrentProject,
      setCurrentScope,
      navigateToLevel,
      navigateToScope,
      navigateToCompany,
      navigateToProject,
      getModuleBasePath,
      getCanonicalPath,
      getModuleScopedPath
    ]
  );

  return <EntityContext.Provider value={value}>{children}</EntityContext.Provider>;
};

export const useEntityContext = (): EntityContextType => {
  const context = useContext(EntityContext);
  if (context === undefined) {
    throw new Error('useEntityContext must be used within an EntityContextProvider');
  }
  return context;
};
