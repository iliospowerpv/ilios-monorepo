import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../api';
import {
  UniversalDescription,
  DescriptionFormSubmitHandler
} from '../../../../../components/forms/UniversalDescription/UniversalDescription';

interface DescriptionProps {
  descriptionText: string | null;
  siteId: number;
  documentId: number;
}

type EditDescriptionMutationArgs = {
  siteId: number;
  documentId: number;
  description: string | null;
};

export const DocumentDescription: React.FC<DescriptionProps> = ({ descriptionText, siteId, documentId }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { mutateAsync: updateDescription } = useMutation({
    mutationFn: (args: EditDescriptionMutationArgs) =>
      ApiClient.dueDiligence.updateDocDescription(args.siteId, args.documentId, args.description)
  });

  const onSubmit: DescriptionFormSubmitHandler = async data => {
    try {
      const response = await updateDescription({
        siteId,
        documentId,
        description: data.description
      });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      notify(response.message || `Document description was successfully updated.`);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating a document description...');
    }
  };

  return <UniversalDescription descriptionText={descriptionText} onSubmitEdit={onSubmit} />;
};

export default DocumentDescription;
