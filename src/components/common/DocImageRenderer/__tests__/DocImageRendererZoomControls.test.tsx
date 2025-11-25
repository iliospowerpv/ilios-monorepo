import { render, screen, fireEvent } from '@testing-library/react';
import { useControls } from 'react-zoom-pan-pinch';

import { DocImageRendererZoomControls } from '../../../../components/common/DocImageRenderer/DocImageRendererZoomControls';

jest.mock('react-zoom-pan-pinch', () => ({
  useControls: jest.fn()
}));

describe('DocImageRendererZoomControls component', () => {
  it('should render and function correctly', async () => {
    const zoomInMockFn = jest.fn();
    const zoomOutMockFn = jest.fn();
    const resetTransformMockFn = jest.fn();

    if (jest.isMockFunction(useControls)) {
      useControls.mockReturnValue({
        zoomIn: zoomInMockFn,
        zoomOut: zoomOutMockFn,
        resetTransform: resetTransformMockFn
      });
    }

    render(<DocImageRendererZoomControls />);

    const zoomInBtn = screen.getByTestId('image-preview-controls-zoom-in');
    const zoomOutBtn = screen.getByTestId('image-preview-controls-zoom-out');
    const zoomResetBtn = screen.getByTestId('image-preview-controls-zoom-reset');

    fireEvent.mouseDown(zoomInBtn);
    fireEvent.mouseDown(zoomOutBtn);
    fireEvent.mouseDown(zoomResetBtn);

    expect(zoomInMockFn).toHaveBeenCalledTimes(1);
    expect(zoomOutMockFn).toHaveBeenCalledTimes(1);
    expect(resetTransformMockFn).toHaveBeenCalledTimes(1);
  });
});
