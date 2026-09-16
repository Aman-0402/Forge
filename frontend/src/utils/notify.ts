// Popup notifications for the app: transient toasts (toastr) for success/error
// feedback, and modal dialogs (SweetAlert2) for confirming destructive actions.
// Imported this way, not inline elsewhere, so the jQuery-global side effect always
// runs before toastr's module does — see jquery-global.ts.
import "./jquery-global";
import toastr from "toastr";
import "toastr/build/toastr.min.css";
import Swal from "sweetalert2";

toastr.options = {
  closeButton: true,
  progressBar: true,
  positionClass: "toast-top-right",
  timeOut: 4000,
  newestOnTop: true,
};

export const toast = {
  success: (message: string, title?: string) => toastr.success(message, title),
  error: (message: string, title?: string) => toastr.error(message, title),
  info: (message: string, title?: string) => toastr.info(message, title),
  warning: (message: string, title?: string) => toastr.warning(message, title),
};

/** Replaces window.confirm for destructive actions. Resolves true if confirmed. */
export async function confirmDialog(opts: {
  title: string;
  text?: string;
  confirmText?: string;
  danger?: boolean;
}): Promise<boolean> {
  const result = await Swal.fire({
    title: opts.title,
    text: opts.text,
    icon: opts.danger ? "warning" : "question",
    showCancelButton: true,
    confirmButtonText: opts.confirmText ?? "Confirm",
    cancelButtonText: "Cancel",
    confirmButtonColor: opts.danger ? "#b3261e" : "#2f5fdb",
    focusCancel: opts.danger,
  });
  return result.isConfirmed;
}

/** Replaces window.prompt. Resolves the entered text, or null if cancelled/blank. */
export async function promptDialog(opts: {
  title: string;
  placeholder?: string;
  confirmText?: string;
  defaultValue?: string;
  /** Allow submitting an empty value (e.g. "clear this override"). Default: no. */
  allowBlank?: boolean;
}): Promise<string | null> {
  const result = await Swal.fire({
    title: opts.title,
    input: "text",
    inputPlaceholder: opts.placeholder,
    inputValue: opts.defaultValue,
    showCancelButton: true,
    confirmButtonText: opts.confirmText ?? "Submit",
    cancelButtonText: "Cancel",
    confirmButtonColor: "#2f5fdb",
    inputValidator: opts.allowBlank ? undefined : (value) => (value?.trim() ? undefined : "This can't be empty."),
  });
  return result.isConfirmed ? (result.value as string) : null;
}

/** A blocking info/success/error modal, for messages that need to be acknowledged
 * (e.g. a one-time invite link) rather than a toast that can be missed. */
export async function alertDialog(opts: {
  title: string;
  html?: string;
  text?: string;
  icon?: "success" | "error" | "info" | "warning";
}): Promise<void> {
  await Swal.fire({
    title: opts.title,
    html: opts.html,
    text: opts.text,
    icon: opts.icon ?? "info",
    confirmButtonColor: "#2f5fdb",
  });
}
