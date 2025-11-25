import React from 'react';

import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import CommunicationIPForm from '../../components/CommunicationIPForm/CommunicationIPForm';

const MBODGateway = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>((props, ref) => (
  <CommunicationIPForm {...props} ref={ref} />
));

MBODGateway.displayName = 'MBODGateway';

export default MBODGateway;
