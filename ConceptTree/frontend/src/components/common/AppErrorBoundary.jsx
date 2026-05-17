import React from "react";

export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[AppErrorBoundary]", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.assign("/");
  };

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-6 text-zinc-900">
        <div className="w-full max-w-md rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-400">
            页面遇到错误
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-zinc-900">
            当前操作没有保存成功
          </h1>
          <p className="mt-3 text-sm leading-6 text-zinc-500">
            页面已拦截异常，避免影响整个应用。你可以刷新后重试，或先回到首页。
          </p>
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={this.handleReload}
              className="flex-1 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700"
            >
              刷新重试
            </button>
            <button
              type="button"
              onClick={this.handleHome}
              className="flex-1 rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-medium text-zinc-600 transition-colors hover:border-zinc-300 hover:text-zinc-900"
            >
              回到首页
            </button>
          </div>
        </div>
      </div>
    );
  }
}
