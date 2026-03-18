import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourceList } from './ResourceList';

describe('ResourceList', () => {
  it('renders nothing when resources is empty', () => {
    const { container } = render(<ResourceList resources={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when resources is null', () => {
    const { container } = render(<ResourceList resources={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders resource name and reason', () => {
    render(<ResourceList resources={[{ name: '3Blue1Brown', url: 'https://example.com', reason: '视觉化讲解' }]} />);
    expect(screen.getByText('3Blue1Brown')).toBeInTheDocument();
    expect(screen.getByText('视觉化讲解')).toBeInTheDocument();
  });

  it('renders link with correct href and target blank', () => {
    render(<ResourceList resources={[{ name: '教程', url: 'https://test.com', reason: '' }]} />);
    const link = screen.getByRole('link', { name: /教程/ });
    expect(link).toHaveAttribute('href', 'https://test.com');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders multiple resources', () => {
    render(<ResourceList resources={[
      { name: 'A', url: '#', reason: '' },
      { name: 'B', url: '#', reason: '' },
    ]} />);
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });
});
