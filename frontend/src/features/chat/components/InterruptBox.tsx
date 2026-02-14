import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../../../app/hooks";
import { sendMessage } from "../slices/chatSlice";

type Interrupt = {
  key?: string;
  question: string;
  input_type: "type" | "select" | "date" | "confirm";
  options?: string[] | null;
  trip_plan?: string;
};

type Props = {
  interrupt: Interrupt;
  fromDate?: string | null;
  disabled?: boolean;
};

const InterruptBox = ({ interrupt, fromDate, disabled = false }: Props) => {
  const dispatch = useAppDispatch();
  const loading = useAppSelector((state) => state.chat.loading);
  const isDisabled = disabled || loading;

  const [value, setValue] = useState("");
  const [dateValue, setDateValue] = useState("");
  const [showInput, setShowInput] = useState(false);

  const submit = (answer: string) => {
    if (!answer.trim() || isDisabled) return;
    dispatch(sendMessage({ interruptAnswer: answer }));
    setValue("");
    setDateValue("");
  };

  const getMinDate = () => {
    if (interrupt.key === "to_date" && fromDate) {
      const [d, m, y] = fromDate.split(".");
      const nextDay = new Date(+y, +m - 1, +d);
      nextDay.setDate(nextDay.getDate() + 1);
      return nextDay.toISOString().split("T")[0];
    }
    return new Date().toISOString().split("T")[0];
  };

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedDate = e.target.value;
    setDateValue(selectedDate);
    const [y, m, d] = selectedDate.split("-");
    setValue(`${d}.${m}.${y}`);
  };

  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: 8,
        padding: 12,
        margin: "10px 0",
        background: "#f9f9f9",
        opacity: isDisabled ? 0.5 : 1,
        pointerEvents: isDisabled ? "none" : "auto",
      }}
    >
      {interrupt.trip_plan && (
        <div
          style={{
            background: "white",
            padding: 12,
            borderRadius: 6,
            marginBottom: 12,
            border: "1px solid #ddd",
            maxHeight: 300,
            overflow: "auto",
          }}
        >
          <div style={{ fontWeight: "bold", marginBottom: 8 }}>
            Your Trip Plan
          </div>
          <div dangerouslySetInnerHTML={{
                  __html: interrupt.trip_plan
                    .replace(/### (.*?)(\n|$)/g, "<h3>$1</h3>")
                    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"),
                }} style={{ whiteSpace: "pre-wrap" }}/>
        </div>
      )}

      <div style={{ fontWeight: "bold", marginBottom: 8 }}>
        {interrupt.question}
      </div>

      {(interrupt.input_type === "confirm" || interrupt.input_type === "select") && (
        <>
          {interrupt.options?.map((opt) => (
            <button
              key={opt}
              onClick={() => submit(opt)}
              disabled={isDisabled}
              style={{ marginRight: 6 }}
            >
              {opt}
            </button>
          ))}
          <div style={{ marginTop: 8 }}>
            <button
              onClick={() => setShowInput(!showInput)}
              disabled={isDisabled}
              style={{ fontSize: 12 }}
            >
              {showInput ? "Hide" : "Or type your response"}
            </button>
          </div>
        </>
      )}

      {interrupt.input_type === "date" && (
        <div style={{ marginTop: 8 }}>
          <input
            type="date"
            value={dateValue}
            min={getMinDate()}
            disabled={isDisabled}
            onChange={handleDateChange}
            style={{ marginRight: 6, padding: 4 }}
          />
          {value && (
            <button disabled={isDisabled} onClick={() => submit(value)}>
              Confirm {value}
            </button>
          )}
        </div>
      )}

      {interrupt.input_type === "type" && (
        <div style={{ marginTop: 8 }}>
          <input
            type="text"
            value={value}
            disabled={isDisabled}
            onChange={(e) => setValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && submit(value)}
            style={{ marginRight: 6, width: "70%" }}
          />
          <button disabled={isDisabled} onClick={() => submit(value)}>
            Send
          </button>
        </div>
      )}

      {showInput && (
        <div style={{ marginTop: 8 }}>
          <input
            type="text"
            value={value}
            disabled={isDisabled}
            onChange={(e) => setValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && submit(value)}
            
            style={{ marginRight: 6 ,  }}
          />
          <button disabled={isDisabled} onClick={() => submit(value)}>
            Send
          </button>
        </div>
      )}

     
    </div>
  );
};

export default InterruptBox;