#![doc = include_str!("../README.md")]

/// Common authoring and rendering components demonstrated by rustdoc.
#[doc = include_str!("../component-reference.md")]
pub mod component_reference {}

/// Controls how an adapter handles generator warnings.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WarningPolicy {
    /// Report warnings without failing the build.
    Report,
    /// Treat every warning as a failed build.
    Fail,
}

/// A framework-neutral documentation target.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DocumentationTarget {
    name: String,
    framework: String,
    policy: WarningPolicy,
}

impl DocumentationTarget {
    /// Creates a new documentation target.
    pub fn new(
        name: impl Into<String>,
        framework: impl Into<String>,
        policy: WarningPolicy,
    ) -> Self {
        Self {
            name: name.into(),
            framework: framework.into(),
            policy,
        }
    }

    /// Returns the stable target name.
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Returns the upstream documentation framework.
    pub fn framework(&self) -> &str {
        &self.framework
    }

    /// Returns the target's warning policy.
    pub fn warning_policy(&self) -> WarningPolicy {
        self.policy
    }
}

/// Selects targets that use `framework`, preserving their original order.
pub fn select_by_framework<'a>(
    targets: &'a [DocumentationTarget],
    framework: &str,
) -> Vec<&'a DocumentationTarget> {
    targets
        .iter()
        .filter(|target| target.framework() == framework)
        .collect()
}
