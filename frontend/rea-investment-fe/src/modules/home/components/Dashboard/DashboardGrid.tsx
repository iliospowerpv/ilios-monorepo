import React, { useState, useEffect, useCallback } from 'react';
import GridLayout from 'react-grid-layout';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import AddIcon from '@mui/icons-material/Add';
import RestoreIcon from '@mui/icons-material/Restore';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import { WidgetWrapper } from './WidgetWrapper';
import { AddWidgetDialog } from './AddWidgetDialog';
import { WIDGET_DEFINITIONS, DEFAULT_VISIBLE_WIDGETS, getDefaultLayout } from './widgetRegistry';

const STORAGE_KEY_LAYOUT = 'home-dashboard-layout';
const STORAGE_KEY_WIDGETS = 'home-dashboard-widgets';

interface LayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

interface DashboardGridProps {
  widgetComponents: Record<string, React.ReactNode>;
  containerWidth?: number;
}

export const DashboardGrid: React.FC<DashboardGridProps> = ({ widgetComponents, containerWidth = 1200 }) => {
  const [layout, setLayout] = useState<LayoutItem[]>([]);
  const [visibleWidgets, setVisibleWidgets] = useState<string[]>([]);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const savedLayout = localStorage.getItem(STORAGE_KEY_LAYOUT);
    const savedWidgets = localStorage.getItem(STORAGE_KEY_WIDGETS);

    if (savedWidgets) {
      const widgets = JSON.parse(savedWidgets) as string[];
      setVisibleWidgets(widgets);
      if (savedLayout) {
        setLayout(JSON.parse(savedLayout) as LayoutItem[]);
      } else {
        setLayout(getDefaultLayout(widgets) as LayoutItem[]);
      }
    } else {
      setVisibleWidgets(DEFAULT_VISIBLE_WIDGETS);
      setLayout(getDefaultLayout(DEFAULT_VISIBLE_WIDGETS) as LayoutItem[]);
    }
    setIsInitialized(true);
  }, []);

  useEffect(() => {
    if (isInitialized && visibleWidgets.length > 0) {
      localStorage.setItem(STORAGE_KEY_WIDGETS, JSON.stringify(visibleWidgets));
    }
  }, [visibleWidgets, isInitialized]);

  useEffect(() => {
    if (isInitialized && layout.length > 0) {
      localStorage.setItem(STORAGE_KEY_LAYOUT, JSON.stringify(layout));
    }
  }, [layout, isInitialized]);

  const handleLayoutChange = useCallback((newLayout: LayoutItem[]) => {
    setLayout(newLayout);
  }, []);

  const handleRemoveWidget = useCallback((widgetId: string) => {
    setVisibleWidgets(prev => prev.filter(id => id !== widgetId));
    setLayout(prev => prev.filter(item => item.i !== widgetId));
  }, []);

  const handleAddWidget = useCallback(
    (widgetId: string) => {
      const widget = WIDGET_DEFINITIONS[widgetId];
      if (!widget) return;

      const maxY = layout.reduce((max, item) => Math.max(max, item.y + item.h), 0);

      const newLayoutItem: LayoutItem = {
        i: widgetId,
        x: 0,
        y: maxY,
        w: widget.defaultWidth,
        h: widget.defaultHeight,
        minW: widget.minWidth,
        minH: widget.minHeight
      };

      setVisibleWidgets(prev => [...prev, widgetId]);
      setLayout(prev => [...prev, newLayoutItem]);
    },
    [layout]
  );

  const handleResetLayout = useCallback(() => {
    setVisibleWidgets(DEFAULT_VISIBLE_WIDGETS);
    setLayout(getDefaultLayout(DEFAULT_VISIBLE_WIDGETS) as LayoutItem[]);
    localStorage.removeItem(STORAGE_KEY_LAYOUT);
    localStorage.removeItem(STORAGE_KEY_WIDGETS);
  }, []);

  if (!isInitialized) {
    return null;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const GridLayoutComponent = GridLayout as any;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
        <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={() => setAddDialogOpen(true)}>
          Add Widget
        </Button>
        <Button variant="outlined" size="small" startIcon={<RestoreIcon />} onClick={handleResetLayout}>
          Reset Layout
        </Button>
      </Box>

      <GridLayoutComponent
        className="layout"
        layout={layout}
        cols={12}
        rowHeight={80}
        width={containerWidth}
        onLayoutChange={handleLayoutChange}
        draggableHandle=".drag-handle"
        isResizable={true}
        isDraggable={true}
        compactType="vertical"
        preventCollision={false}
      >
        {visibleWidgets.map(widgetId => (
          <div key={widgetId}>
            <WidgetWrapper
              widgetId={widgetId}
              onRemove={handleRemoveWidget}
              showHeader={widgetId !== 'tasks' && widgetId !== 'notifications'}
            >
              {widgetComponents[widgetId]}
            </WidgetWrapper>
          </div>
        ))}
      </GridLayoutComponent>

      <AddWidgetDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        visibleWidgets={visibleWidgets}
        onAddWidget={handleAddWidget}
      />
    </Box>
  );
};

export default DashboardGrid;
