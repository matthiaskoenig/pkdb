// Compile-time regression checks: upstream declaration corrections must retain
// component prop precision rather than turn the library boundary into `any`.
import type { VBtn, VSelect } from "vuetify/components";

type Assert<Condition extends true> = Condition;
type ButtonVariant = InstanceType<typeof VBtn>["$props"]["variant"];
type SelectVariant = InstanceType<typeof VSelect>["$props"]["variant"];
export type ButtonAcceptsOutlined = Assert<
  "outlined" extends ButtonVariant ? true : false
>;
export type ButtonRejectsUnknownVariant = Assert<
  "not-a-button-variant" extends ButtonVariant ? false : true
>;
export type SelectRejectsUnknownVariant = Assert<
  "not-a-select-variant" extends SelectVariant ? false : true
>;
