export interface WidgetDefinition {
  id: string;
  title: string;
  description: string;
  defaultWidth: number;
  defaultHeight: number;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
}

export const WIDGET_DEFINITIONS: Record<string, WidgetDefinition> = {
  tasks: {
    id: 'tasks',
    title: 'Tasks',
    description: 'View and manage your pending tasks',
    defaultWidth: 8,
    defaultHeight: 4,
    minWidth: 4,
    minHeight: 3
  },
  notifications: {
    id: 'notifications',
    title: 'Notifications',
    description: 'Recent notifications and alerts',
    defaultWidth: 4,
    defaultHeight: 3,
    minWidth: 3,
    minHeight: 2
  },
  quickActions: {
    id: 'quickActions',
    title: 'Quick Actions',
    description: 'Shortcuts to common actions',
    defaultWidth: 4,
    defaultHeight: 3,
    minWidth: 3,
    minHeight: 2
  },
  companies: {
    id: 'companies',
    title: 'Your Companies',
    description: 'Companies you have access to',
    defaultWidth: 12,
    defaultHeight: 4,
    minWidth: 6,
    minHeight: 3
  },
  projects: {
    id: 'projects',
    title: 'Your Projects',
    description: 'Projects you have access to',
    defaultWidth: 12,
    defaultHeight: 4,
    minWidth: 6,
    minHeight: 3
  }
};

export const DEFAULT_VISIBLE_WIDGETS = ['tasks', 'notifications', 'quickActions', 'companies', 'projects'];

export const getDefaultLayout = (visibleWidgets: string[]) => {
  const layout: Array<{ i: string; x: number; y: number; w: number; h: number; minW?: number; minH?: number }> = [];

  visibleWidgets.forEach(widgetId => {
    const widget = WIDGET_DEFINITIONS[widgetId];
    if (!widget) return;

    if (widgetId === 'tasks') {
      layout.push({
        i: widgetId,
        x: 0,
        y: 0,
        w: widget.defaultWidth,
        h: widget.defaultHeight,
        minW: widget.minWidth,
        minH: widget.minHeight
      });
    } else if (widgetId === 'notifications') {
      layout.push({
        i: widgetId,
        x: 8,
        y: 0,
        w: widget.defaultWidth,
        h: widget.defaultHeight,
        minW: widget.minWidth,
        minH: widget.minHeight
      });
    } else if (widgetId === 'quickActions') {
      layout.push({
        i: widgetId,
        x: 8,
        y: 3,
        w: widget.defaultWidth,
        h: widget.defaultHeight,
        minW: widget.minWidth,
        minH: widget.minHeight
      });
    } else if (widgetId === 'companies') {
      layout.push({
        i: widgetId,
        x: 0,
        y: 6,
        w: widget.defaultWidth,
        h: widget.defaultHeight,
        minW: widget.minWidth,
        minH: widget.minHeight
      });
    } else if (widgetId === 'projects') {
      layout.push({
        i: widgetId,
        x: 0,
        y: 10,
        w: widget.defaultWidth,
        h: widget.defaultHeight,
        minW: widget.minWidth,
        minH: widget.minHeight
      });
    }
  });

  return layout;
};
