/* ----------------------------------------------------------------------------
 * GTSAM Copyright 2010, Georgia Tech Research Corporation,
 * Atlanta, Georgia 30332-0415
 * All Rights Reserved
 * Authors: Frank Dellaert, et al. (see THANKS for the full author list)
 * See LICENSE for the license information
 * -------------------------------------------------------------------------- */

/**
 * @file    HybridBayesNet.h
 * @brief   A Bayes net of Gaussian Conditionals indexed by discrete keys.
 * @author  Varun Agrawal
 * @author  Fan Jiang
 * @author  Frank Dellaert
 * @date    December 2021
 */

#pragma once

#include <gtsam/discrete/DecisionTreeFactor.h>
#include <gtsam/global_includes.h>
#include <gtsam/hybrid/HybridConditional.h>
#include <gtsam/hybrid/HybridValues.h>
#include <gtsam/inference/BayesNet.h>
#include <gtsam/linear/GaussianBayesNet.h>

namespace gtsam {

/**
 * A hybrid Bayes net is a collection of HybridConditionals, which can have
 * discrete conditionals, Gaussian mixtures, or pure Gaussian conditionals.
 *
 * @ingroup hybrid
 */
class GTSAM_EXPORT HybridBayesNet : public BayesNet<HybridConditional> {
 public:
  using Base = BayesNet<HybridConditional>;
  using This = HybridBayesNet;
  using ConditionalType = HybridConditional;
  using shared_ptr = boost::shared_ptr<HybridBayesNet>;
  using sharedConditional = boost::shared_ptr<ConditionalType>;

  /// @name Standard Constructors
  /// @{

  /** Construct empty Bayes net */
  HybridBayesNet() = default;

  /// @}
  /// @name Testable
  /// @{

  /// GTSAM-style printing
  void print(
      const std::string &s = "",
      const KeyFormatter &formatter = DefaultKeyFormatter) const override;

  /// GTSAM-style equals
  bool equals(const This& fg, double tol = 1e-9) const;
  
  /// @}
  /// @name Standard Interface
  /// @{

  /// Add HybridConditional to Bayes Net
  using Base::emplace_shared;

  /// Add a conditional directly using a pointer.
  template <class Conditional>
  void emplace_back(Conditional *conditional) {
    factors_.push_back(boost::make_shared<HybridConditional>(
        boost::shared_ptr<Conditional>(conditional)));
  }

  /// Add a conditional directly using a shared_ptr.
  void push_back(boost::shared_ptr<HybridConditional> conditional) {
    factors_.push_back(conditional);
  }

  /// Add a conditional directly using implicit conversion.
  void push_back(HybridConditional &&conditional) {
    factors_.push_back(
        boost::make_shared<HybridConditional>(std::move(conditional)));
  }

  /**
   * @brief Get the Gaussian Bayes Net which corresponds to a specific discrete
   * value assignment.
   *
   * @param assignment The discrete value assignment for the discrete keys.
   * @return GaussianBayesNet
   */
  GaussianBayesNet choose(const DiscreteValues &assignment) const;

  /// Evaluate hybrid probability density for given HybridValues.
  double evaluate(const HybridValues &values) const;

  /// Evaluate hybrid probability density for given HybridValues, sugar.
  double operator()(const HybridValues &values) const {
    return evaluate(values);
  }

  /**
   * @brief Solve the HybridBayesNet by first computing the MPE of all the
   * discrete variables and then optimizing the continuous variables based on
   * the MPE assignment.
   *
   * @return HybridValues
   */
  HybridValues optimize() const;

  /**
   * @brief Given the discrete assignment, return the optimized estimate for the
   * selected Gaussian BayesNet.
   *
   * @param assignment An assignment of discrete values.
   * @return Values
   */
  VectorValues optimize(const DiscreteValues &assignment) const;

  /**
   * @brief Get all the discrete conditionals as a decision tree factor.
   *
   * @return DecisionTreeFactor::shared_ptr
   */
  DecisionTreeFactor::shared_ptr discreteConditionals() const;

  /**
   * @brief Sample from an incomplete BayesNet, given missing variables.
   *
   * Example:
   *   std::mt19937_64 rng(42);
   *   VectorValues given = ...;
   *   auto sample = bn.sample(given, &rng);
   *
   * @param given Values of missing variables.
   * @param rng The pseudo-random number generator.
   * @return HybridValues
   */
  HybridValues sample(const HybridValues &given, std::mt19937_64 *rng) const;

  /**
   * @brief Sample using ancestral sampling.
   *
   * Example:
   *   std::mt19937_64 rng(42);
   *   auto sample = bn.sample(&rng);
   *
   * @param rng The pseudo-random number generator.
   * @return HybridValues
   */
  HybridValues sample(std::mt19937_64 *rng) const;

  /**
   * @brief Sample from an incomplete BayesNet, use default rng.
   *
   * @param given Values of missing variables.
   * @return HybridValues
   */
  HybridValues sample(const HybridValues &given) const;

  /**
   * @brief Sample using ancestral sampling, use default rng.
   *
   * @return HybridValues
   */
  HybridValues sample() const;

  /// Prune the Hybrid Bayes Net such that we have at most maxNrLeaves leaves.
  HybridBayesNet prune(size_t maxNrLeaves);

  /**
   * @brief 0.5 * sum of squared Mahalanobis distances
   * for a specific discrete assignment.
   *
   * @param values Continuous values and discrete assignment.
   * @return double
   */
  double error(const HybridValues &values) const;

  /**
   * @brief Compute conditional error for each discrete assignment,
   * and return as a tree.
   *
   * @param continuousValues Continuous values at which to compute the error.
   * @return AlgebraicDecisionTree<Key>
   */
  AlgebraicDecisionTree<Key> error(const VectorValues &continuousValues) const;

  /**
   * @brief Compute unnormalized probability q(μ|M),
   * for each discrete assignment, and return as a tree.
   * q(μ|M) is the unnormalized probability at the MLE point μ,
   * conditioned on the discrete variables.
   *
   * @param continuousValues Continuous values at which to compute the
   * probability.
   * @return AlgebraicDecisionTree<Key>
   */
  AlgebraicDecisionTree<Key> probPrime(
      const VectorValues &continuousValues) const;

  /**
   * Convert a hybrid Bayes net to a hybrid Gaussian factor graph by converting
   * all conditionals with instantiated measurements into likelihood factors.
   */
  HybridGaussianFactorGraph toFactorGraph(
      const VectorValues &measurements) const;
  /// @}

 private:
  /**
   * @brief Update the discrete conditionals with the pruned versions.
   *
   * @param prunedDecisionTree
   */
  void updateDiscreteConditionals(
      const DecisionTreeFactor::shared_ptr &prunedDecisionTree);

  /** Serialization function */
  friend class boost::serialization::access;
  template <class ARCHIVE>
  void serialize(ARCHIVE &ar, const unsigned int /*version*/) {
    ar &BOOST_SERIALIZATION_BASE_OBJECT_NVP(Base);
  }
};

/// traits
template <>
struct traits<HybridBayesNet> : public Testable<HybridBayesNet> {};

}  // namespace gtsam
