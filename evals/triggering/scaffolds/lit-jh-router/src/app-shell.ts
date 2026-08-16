import { LitElement, html } from "lit";
import { customElement } from "lit/decorators.js";
import { Routes } from "@lit-labs/router";
import "@jack-henry/jh-ui/jh-button";

@customElement("app-shell")
export class AppShell extends LitElement {
  private routes = new Routes(this, [
    { path: "/", render: () => html`<tl-overview></tl-overview>` },
  ]);
  render() {
    return html`<jh-button>Go</jh-button>${this.routes.outlet()}`;
  }
}
