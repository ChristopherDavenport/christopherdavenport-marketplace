import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("tl-stat")
export class TlStat extends LitElement {
  static styles = css`
    :host { display: block; }
  `;
  @property({ type: String }) label = "";
  @property({ type: Number }) value = 0;
  @property({ type: Array }) rows = [];
  render() {
    return html`<span>${this.label}: ${this.value}</span>`;
  }
}
