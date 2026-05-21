import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MasteryChecklist } from './MasteryChecklist';

describe('MasteryChecklist', () => {
  it('renders nothing when items is empty', () => {
    const { container } = render(<MasteryChecklist items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when items is null', () => {
    const { container } = render(<MasteryChecklist items={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders section with mastery items', () => {
    render(<MasteryChecklist items={['手算 2x3 矩阵相乘', '判断矩阵能否相乘']} />);
    expect(screen.getByTestId('mastery-section')).toBeInTheDocument();
    expect(screen.getByText('手算 2x3 矩阵相乘')).toBeInTheDocument();
    expect(screen.getByText('判断矩阵能否相乘')).toBeInTheDocument();
  });

  it('renders correct count of items', () => {
    render(<MasteryChecklist items={['item1', 'item2', 'item3']} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
  });

  it('starts quiz when clicking a mastery item', () => {
    const calls = [];
    render(
      <MasteryChecklist
        items={['item1']}
        onStartQuiz={(item, index) => calls.push({ item, index })}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /item1/ }));
    expect(calls).toEqual([{ item: 'item1', index: 0 }]);
  });

  it('shows passed item with checked state', () => {
    render(
      <MasteryChecklist
        items={['item1']}
        getItemKey={() => 'node:0:item1'}
        passedKeys={new Set(['node:0:item1'])}
      />,
    );

    expect(screen.getByRole('button', { name: /item1/ })).toHaveClass('text-teal-800');
  });
});
