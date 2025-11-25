import React from 'react';

import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import CommunicationIPForm from '../../components/CommunicationIPForm/CommunicationIPForm';

const Camera = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>((props, ref) => (
  <CommunicationIPForm {...props} ref={ref} />
));

Camera.displayName = 'Camera';

export default Camera;
