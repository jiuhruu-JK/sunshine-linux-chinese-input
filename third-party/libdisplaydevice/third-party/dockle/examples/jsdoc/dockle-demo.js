/**
 * Utilities for describing a documentation build.
 * @module dockle-demo
 */

/** A documentation target consumed by Dockle. */
export class DocumentationTarget {
  /**
   * Create a target.
   * @param {string} name Stable name used for the output directory.
   * @param {string} framework Upstream documentation framework.
   * @param {WarningPolicy} policy Warning behavior for the generator.
   */
  constructor(name, framework, policy) {
    this.name = name;
    this.framework = framework;
    this.policy = policy;
  }

  /**
   * Return a human-readable summary.
   * @returns {string} Target and framework joined for display.
   */
  summary() {
    return `${this.name} (${this.framework})`;
  }
}

/** Warning behavior for a documentation generator. */
export const WarningPolicy = Object.freeze({
  Report: "report",
  Fail: "fail",
});

/**
 * Select targets matching a framework.
 * @param {DocumentationTarget[]} targets Candidate documentation targets.
 * @param {string} framework Framework to select.
 * @returns {DocumentationTarget[]} Matching targets in their original order.
 */
export function selectByFramework(targets, framework) {
  return targets.filter((target) => target.framework === framework);
}
