// toastr's UMD build checks for a global `jQuery`/`$`, which a normal ES import of the
// "jquery" package does not create (it's just a module-scoped binding). This file's only
// job is that side effect, and it must be imported before toastr anywhere in the app —
// see notify.ts, which imports this first for exactly that reason.
import $ from "jquery";

declare global {
  interface Window {
    jQuery: typeof $;
    $: typeof $;
  }
}

window.jQuery = $;
window.$ = $;
