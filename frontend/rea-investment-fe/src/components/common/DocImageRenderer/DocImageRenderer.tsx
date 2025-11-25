import React from 'react';
import { DocRenderer } from '@cyntler/react-doc-viewer';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import Box from '@mui/material/Box';

import { DocImageRendererZoomControls } from './DocImageRendererZoomControls';

const DocImageRenderer: DocRenderer = props => {
  const {
    mainState: { currentDocument }
  } = props;
  const backgroundColor = '#FAFAFA';
  const scaleUp = false;
  const zoomFactor = 8;

  const [container, setContainer] = React.useState<HTMLDivElement | null>(null);

  const [containerWidth, setContainerWidth] = React.useState<number>(0);
  const [containerHeight, setContainerHeight] = React.useState<number>(0);

  const [imageNaturalWidth, setImageNaturalWidth] = React.useState<number>(0);
  const [imageNaturalHeight, setImageNaturalHeight] = React.useState<number>(0);

  const imageScale = React.useMemo(() => {
    if (containerWidth === 0 || containerHeight === 0 || imageNaturalWidth === 0 || imageNaturalHeight === 0) return 0;
    const scale = Math.min(containerWidth / imageNaturalWidth, containerHeight / imageNaturalHeight);
    return scaleUp ? scale : Math.min(scale, 1);
  }, [scaleUp, containerWidth, containerHeight, imageNaturalWidth, imageNaturalHeight]);

  const handleResize = React.useCallback(() => {
    if (container !== null) {
      const rect = container.getBoundingClientRect();
      setContainerWidth(rect.width);
      setContainerHeight(rect.height);
    } else {
      setContainerWidth(0);
      setContainerHeight(0);
    }
  }, [container]);

  React.useEffect(() => {
    handleResize();
    if (container) {
      const observer = new ResizeObserver(handleResize);
      observer.observe(container);

      return () => {
        observer.unobserve(container);
        observer.disconnect();
      };
    }
  }, [handleResize, container]);

  const handleImageOnLoad = (image: HTMLImageElement) => {
    setImageNaturalWidth(image.naturalWidth);
    setImageNaturalHeight(image.naturalHeight);
  };

  React.useEffect(() => {
    if (!currentDocument?.fileData || typeof currentDocument.fileData !== 'string') return;
    const image = new Image();
    image.onload = () => handleImageOnLoad(image);
    image.src = currentDocument.fileData;
  }, [currentDocument]);

  if (!currentDocument?.fileData || typeof currentDocument.fileData !== 'string') return null;

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        backgroundColor
      }}
      data-testid="doc-image-renderer-container"
      ref={(el: HTMLDivElement | null) => setContainer(el)}
    >
      {imageScale > 0 && (
        <TransformWrapper
          key={`${containerWidth}x${containerHeight}`}
          centerOnInit
          initialScale={imageScale * 0.95}
          minScale={imageScale * 0.5}
          maxScale={imageScale * zoomFactor}
        >
          <DocImageRendererZoomControls />
          <TransformComponent
            wrapperStyle={{
              display: 'flex',
              flex: 1,
              width: '100%',
              height: '100%',
              backgroundColor: '#fff'
            }}
          >
            <img src={currentDocument.fileData} alt="current document image" />
          </TransformComponent>
        </TransformWrapper>
      )}
    </Box>
  );
};

DocImageRenderer.fileTypes = ['png', 'image/png', 'jpeg', 'image/jpeg', 'jpg', 'image/jpg'];
DocImageRenderer.weight = 1;

export { DocImageRenderer };
export default DocImageRenderer;
