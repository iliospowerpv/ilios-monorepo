import React from 'react';

import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import CommunicationIPForm from '../../components/CommunicationIPForm/CommunicationIPForm';

const NetworkGateway = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  (props, ref) => <CommunicationIPForm {...props} ref={ref} />
);

NetworkGateway.displayName = 'NetworkGateway';

export default NetworkGateway;
