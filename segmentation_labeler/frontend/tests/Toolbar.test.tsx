import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { Toolbar } from "../src/components/Toolbar";

it("selects tools, changes brush size, and exposes history and save state", async () => {
  const user = userEvent.setup();
  const onTool = vi.fn();
  const onBrushSize = vi.fn();
  const onUndo = vi.fn();
  const onRedo = vi.fn();
  render(
    <Toolbar
      tool="brush"
      brushSize={24}
      canUndo
      canRedo
      saveStatus="saving"
      maskVisible
      opacity={0.45}
      onTool={onTool}
      onBrushSize={onBrushSize}
      onUndo={onUndo}
      onRedo={onRedo}
      onClear={vi.fn()}
      onReset={vi.fn()}
      onMaskVisible={vi.fn()}
      onOpacity={vi.fn()}
      onView={vi.fn()}
    />,
  );

  expect(screen.getByText("Saving")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Eraser/ }));
  expect(onTool).toHaveBeenCalledWith("eraser");
  await user.click(screen.getByRole("button", { name: /Undo/ }));
  await user.click(screen.getByRole("button", { name: /Redo/ }));
  expect(onUndo).toHaveBeenCalledOnce();
  expect(onRedo).toHaveBeenCalledOnce();

  fireEvent.change(screen.getByLabelText("Brush size"), { target: { value: "40" } });
  expect(onBrushSize).toHaveBeenCalledWith(40);
});
