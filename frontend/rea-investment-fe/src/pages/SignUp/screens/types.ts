interface SignUpScreenProps {
  email: string;
  token: string;
  formSubmit: (data: SignUpFormInputs) => Promise<void>;
  isSubmitPending: boolean;
  errorMessage?: string;
  failureReason?: string;
}

interface SignUpFormInputs {
  password: string;
  confirmPassword: string;
}

export type { SignUpFormInputs, SignUpScreenProps };
