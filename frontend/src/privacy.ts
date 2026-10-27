export const privacyPolicyVersion = import.meta.env.VITE_PRIVACY_POLICY_VERSION || "2026-10-27-v2";

export const privacyController = {
  name: import.meta.env.VITE_PRIVACY_CONTROLLER_NAME?.trim() || "",
  identification: import.meta.env.VITE_PRIVACY_CONTROLLER_ID?.trim() || "",
  address: import.meta.env.VITE_PRIVACY_CONTROLLER_ADDRESS?.trim() || "",
  email: import.meta.env.VITE_PRIVACY_CONTACT_EMAIL?.trim() || "",
  phone: import.meta.env.VITE_PRIVACY_CONTACT_PHONE?.trim() || "",
  retention: import.meta.env.VITE_PRIVACY_RETENTION_POLICY?.trim() || "",
};

export const privacyIdentityComplete = Boolean(
  privacyController.name && privacyController.address && privacyController.email && privacyController.phone && privacyController.retention,
);
