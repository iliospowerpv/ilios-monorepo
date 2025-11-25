import { cloneDeep } from 'lodash';

export type Crumb = {
  title: string;
  link?: string;
};
export type Crumbs = Crumb[];

type CrumbsBuilder = { (data?: unknown): Crumbs } | { (): Crumbs };

type ModuleId =
  | 'asset-management'
  | 'operations-and-maintenance'
  | 'dashboard'
  | 'due-diligence'
  | 'my-portfolio'
  | 'reports';

interface AIAssistantConfig {
  generateConfig: (data?: unknown) => {
    enabled: boolean;
    siteId: number;
  };
}

interface ModuleFeaturesMap {
  ['ai-assistant']?: AIAssistantConfig;
}

interface RouteHandleParams {
  moduleId?: ModuleId;
  crumbsBuilder?: CrumbsBuilder;
  enabledFeatures?: ModuleFeaturesMap;
}

export class RouteHandle {
  private crumbsBuilder: CrumbsBuilder | null;
  private moduleId: string | null;
  private enabledFeatures: ModuleFeaturesMap;

  private constructor(
    moduleId: string | null,
    crumbsBuilder: CrumbsBuilder | null,
    enabledFeatures?: ModuleFeaturesMap
  ) {
    this.moduleId = moduleId;
    this.crumbsBuilder = crumbsBuilder;
    this.enabledFeatures = enabledFeatures ? cloneDeep(enabledFeatures) : {};
  }

  public buildCrumbs(data: unknown): Crumbs {
    const builder = this.crumbsBuilder;
    return builder ? builder(data) : [];
  }

  public getModuleId(): string | null {
    return this.moduleId;
  }

  public getFeaturesMap(): ModuleFeaturesMap {
    return cloneDeep(this.enabledFeatures);
  }

  public static createHandle(params: RouteHandleParams) {
    const { moduleId, crumbsBuilder, enabledFeatures } = params;

    return new RouteHandle(moduleId ?? null, crumbsBuilder ?? null, enabledFeatures);
  }
}
