export type InterruptPayload = {
  type: "interrupt";
  key: string;
  question: string;
  input_type: "type" | "select" | "date" | "confirm";
  options?: string[] | null;
  default?: string | null;
  trip_plan?: string;
};

export type Message =
  | {
      sender: "user" | "bot";
      text: string;
    }
  | {
      sender: "bot";
      interrupt: InterruptPayload;
    };


    