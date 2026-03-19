/**
 * MasteryChecklist tests — verify that mastery items render correctly and that
 * the component is invisible when given no items.
 *
 * Coverage:
 *  - Empty/null guard: component renders nothing when items is empty or null
 *  - Section presence: the mastery-section container appears with valid input
 *  - Item text: each string in the items array is rendered in the document
 *  - Item count: the rendered list contains exactly as many items as the input array
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
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
});
