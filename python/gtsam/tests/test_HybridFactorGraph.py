"""
GTSAM Copyright 2010-2019, Georgia Tech Research Corporation,
Atlanta, Georgia 30332-0415
All Rights Reserved

See LICENSE for the license information

Unit tests for Hybrid Factor Graphs.
Author: Fan Jiang, Varun Agrawal, Frank Dellaert
"""
# pylint: disable=invalid-name, no-name-in-module, no-member

import unittest

import numpy as np
from gtsam.symbol_shorthand import C, M, X, Z
from gtsam.utils.test_case import GtsamTestCase

import gtsam
from gtsam import (DiscreteConditional, DiscreteKeys, GaussianConditional,
                   GaussianMixture, GaussianMixtureFactor, HybridBayesNet,
                   HybridGaussianFactorGraph, HybridValues, JacobianFactor,
                   Ordering, noiseModel)


class TestHybridGaussianFactorGraph(GtsamTestCase):
    """Unit tests for HybridGaussianFactorGraph."""

    def test_create(self):
        """Test construction of hybrid factor graph."""
        model = noiseModel.Unit.Create(3)
        dk = DiscreteKeys()
        dk.push_back((C(0), 2))

        jf1 = JacobianFactor(X(0), np.eye(3), np.zeros((3, 1)), model)
        jf2 = JacobianFactor(X(0), np.eye(3), np.ones((3, 1)), model)

        gmf = GaussianMixtureFactor([X(0)], dk, [jf1, jf2])

        hfg = HybridGaussianFactorGraph()
        hfg.push_back(jf1)
        hfg.push_back(jf2)
        hfg.push_back(gmf)

        hbn = hfg.eliminateSequential(
            Ordering.ColamdConstrainedLastHybridGaussianFactorGraph(
                hfg, [C(0)]))

        self.assertEqual(hbn.size(), 2)

        mixture = hbn.at(0).inner()
        self.assertIsInstance(mixture, GaussianMixture)
        self.assertEqual(len(mixture.keys()), 2)

        discrete_conditional = hbn.at(hbn.size() - 1).inner()
        self.assertIsInstance(discrete_conditional, DiscreteConditional)

    def test_optimize(self):
        """Test construction of hybrid factor graph."""
        model = noiseModel.Unit.Create(3)
        dk = DiscreteKeys()
        dk.push_back((C(0), 2))

        jf1 = JacobianFactor(X(0), np.eye(3), np.zeros((3, 1)), model)
        jf2 = JacobianFactor(X(0), np.eye(3), np.ones((3, 1)), model)

        gmf = GaussianMixtureFactor([X(0)], dk, [jf1, jf2])

        hfg = HybridGaussianFactorGraph()
        hfg.push_back(jf1)
        hfg.push_back(jf2)
        hfg.push_back(gmf)

        dtf = gtsam.DecisionTreeFactor([(C(0), 2)], "0 1")
        hfg.push_back(dtf)

        hbn = hfg.eliminateSequential(
            Ordering.ColamdConstrainedLastHybridGaussianFactorGraph(
                hfg, [C(0)]))

        hv = hbn.optimize()
        self.assertEqual(hv.atDiscrete(C(0)), 1)

    @staticmethod
    def tiny(num_measurements: int = 1, prior_mean: float = 5.0,
             prior_sigma: float = 0.5) -> HybridBayesNet:
        """
        Create a tiny two variable hybrid model which represents
        the generative probability P(Z, x0, mode) = P(Z|x0, mode)P(x0)P(mode).
        num_measurements: number of measurements in Z = {z0, z1...}
        """
        # Create hybrid Bayes net.
        bayesNet = HybridBayesNet()

        # Create mode key: 0 is low-noise, 1 is high-noise.
        mode = (M(0), 2)

        # Create Gaussian mixture Z(0) = X(0) + noise for each measurement.
        I_1x1 = np.eye(1)
        keys = DiscreteKeys()
        keys.push_back(mode)
        for i in range(num_measurements):
            conditional0 = GaussianConditional.FromMeanAndStddev(Z(i),
                                                                 I_1x1,
                                                                 X(0), [0],
                                                                 sigma=0.5)
            conditional1 = GaussianConditional.FromMeanAndStddev(Z(i),
                                                                 I_1x1,
                                                                 X(0), [0],
                                                                 sigma=3)
            bayesNet.push_back(GaussianMixture([Z(i)], [X(0)], keys,
                                               [conditional0, conditional1]))

        # Create prior on X(0).
        prior_on_x0 = GaussianConditional.FromMeanAndStddev(
            X(0), [prior_mean], prior_sigma)
        bayesNet.push_back(prior_on_x0)

        # Add prior on mode.
        bayesNet.push_back(DiscreteConditional(mode, "4/6"))

        return bayesNet

    def test_evaluate(self):
        """Test evaluate with two different prior noise models."""
        # TODO(dellaert): really a HBN test
        # Create a tiny Bayes net P(x0) P(m0) P(z0|x0)
        bayesNet1 = self.tiny(prior_sigma=0.5, num_measurements=1)
        bayesNet2 = self.tiny(prior_sigma=5.0, num_measurements=1)
        # bn1: # 1/sqrt(2*pi*0.5^2)
        # bn2: # 1/sqrt(2*pi*5.0^2)
        expected_ratio = np.sqrt(2*np.pi*5.0**2)/np.sqrt(2*np.pi*0.5**2)
        mean0 = HybridValues()
        mean0.insert(X(0), [5.0])
        mean0.insert(Z(0), [5.0])
        mean0.insert(M(0), 0)
        self.assertAlmostEqual(bayesNet1.evaluate(mean0) /
                               bayesNet2.evaluate(mean0), expected_ratio,
                               delta=1e-9)
        mean1 = HybridValues()
        mean1.insert(X(0), [5.0])
        mean1.insert(Z(0), [5.0])
        mean1.insert(M(0), 1)
        self.assertAlmostEqual(bayesNet1.evaluate(mean1) /
                               bayesNet2.evaluate(mean1), expected_ratio,
                               delta=1e-9)

    @staticmethod
    def measurements(sample: HybridValues, indices) -> gtsam.VectorValues:
        """Create measurements from a sample, grabbing Z(i) for indices."""
        measurements = gtsam.VectorValues()
        for i in indices:
            measurements.insert(Z(i), sample.at(Z(i)))
        return measurements

    @classmethod
    def factor_graph_from_bayes_net(cls, bayesNet: HybridBayesNet,
                                    sample: HybridValues):
        """Create a factor graph from the Bayes net with sampled measurements.
            The factor graph is `P(x)P(n) ϕ(x, n; z0) ϕ(x, n; z1) ...`
            and thus represents the same joint probability as the Bayes net.
        """
        fg = HybridGaussianFactorGraph()
        num_measurements = bayesNet.size() - 2
        for i in range(num_measurements):
            conditional = bayesNet.at(i).asMixture()
            factor = conditional.likelihood(cls.measurements(sample, [i]))
            fg.push_back(factor)
        fg.push_back(bayesNet.at(num_measurements).asGaussian())
        fg.push_back(bayesNet.at(num_measurements+1).asDiscrete())
        return fg

    @classmethod
    def estimate_marginals(cls, target, proposal_density: HybridBayesNet,
                           N=10000):
        """Do importance sampling to estimate discrete marginal P(mode)."""
        # Allocate space for marginals on mode.
        marginals = np.zeros((2,))

        # Do importance sampling.
        for s in range(N):
            proposed = proposal_density.sample()  # sample from proposal
            target_proposed = target(proposed)  # evaluate target
            # print(target_proposed, proposal_density.evaluate(proposed))
            weight = target_proposed / proposal_density.evaluate(proposed)
            # print weight:
            # print(f"weight: {weight}")
            marginals[proposed.atDiscrete(M(0))] += weight

        # print marginals:
        marginals /= marginals.sum()
        return marginals

    def test_tiny(self):
        """Test a tiny two variable hybrid model."""
        # P(x0)P(mode)P(z0|x0,mode)
        prior_sigma = 0.5
        bayesNet = self.tiny(prior_sigma=prior_sigma)

        # Deterministic values exactly at the mean, for both x and Z:
        values = HybridValues()
        values.insert(X(0), [5.0])
        values.insert(M(0), 0)  # low-noise, standard deviation 0.5
        z0: float = 5.0
        values.insert(Z(0), [z0])

        def unnormalized_posterior(x):
            """Posterior is proportional to joint, centered at 5.0 as well."""
            x.insert(Z(0), [z0])
            return bayesNet.evaluate(x)

        # Create proposal density on (x0, mode), making sure it has same mean:
        posterior_information = 1/(prior_sigma**2) + 1/(0.5**2)
        posterior_sigma = posterior_information**(-0.5)
        proposal_density = self.tiny(
            num_measurements=0, prior_mean=5.0, prior_sigma=posterior_sigma)

        # Estimate marginals using importance sampling.
        marginals = self.estimate_marginals(
            target=unnormalized_posterior, proposal_density=proposal_density)
        # print(f"True mode: {values.atDiscrete(M(0))}")
        # print(f"P(mode=0; Z) = {marginals[0]}")
        # print(f"P(mode=1; Z) = {marginals[1]}")

        # Check that the estimate is close to the true value.
        self.assertAlmostEqual(marginals[0], 0.74, delta=0.01)
        self.assertAlmostEqual(marginals[1], 0.26, delta=0.01)

        fg = self.factor_graph_from_bayes_net(bayesNet, values)
        self.assertEqual(fg.size(), 3)

        # Test elimination.
        ordering = gtsam.Ordering()
        ordering.push_back(X(0))
        ordering.push_back(M(0))
        posterior = fg.eliminateSequential(ordering)

        def true_posterior(x):
            """Posterior from elimination."""
            x.insert(Z(0), [z0])
            return posterior.evaluate(x)

        # Estimate marginals using importance sampling.
        marginals = self.estimate_marginals(
            target=true_posterior, proposal_density=proposal_density)
        # print(f"True mode: {values.atDiscrete(M(0))}")
        # print(f"P(mode=0; z0) = {marginals[0]}")
        # print(f"P(mode=1; z0) = {marginals[1]}")

        # Check that the estimate is close to the true value.
        self.assertAlmostEqual(marginals[0], 0.74, delta=0.01)
        self.assertAlmostEqual(marginals[1], 0.26, delta=0.01)

    @staticmethod
    def calculate_ratio(bayesNet: HybridBayesNet,
                        fg: HybridGaussianFactorGraph,
                        sample: HybridValues):
        """Calculate ratio between Bayes net and factor graph."""
        return bayesNet.evaluate(sample) / fg.probPrime(sample) if \
            fg.probPrime(sample) > 0 else 0

    def test_ratio(self):
        """
        Given a tiny two variable hybrid model, with 2 measurements, test the
        ratio of the bayes net model representing P(z,x,n)=P(z|x, n)P(x)P(n)
        and the factor graph P(x, n | z)=P(x | n, z)P(n|z),
        both of which represent the same posterior.
        """
        # Create generative model P(z, x, n)=P(z|x, n)P(x)P(n)
        prior_sigma = 0.5
        bayesNet = self.tiny(prior_sigma=prior_sigma, num_measurements=2)

        # Deterministic values exactly at the mean, for both x and Z:
        values = HybridValues()
        values.insert(X(0), [5.0])
        values.insert(M(0), 0)  # high-noise, standard deviation 3
        measurements = gtsam.VectorValues()
        measurements.insert(Z(0), [4.0])
        measurements.insert(Z(1), [6.0])
        values.insert(measurements)

        def unnormalized_posterior(x):
            """Posterior is proportional to joint, centered at 5.0 as well."""
            x.insert(measurements)
            return bayesNet.evaluate(x)

        # Create proposal density on (x0, mode), making sure it has same mean:
        posterior_information = 1/(prior_sigma**2) + 2.0/(3.0**2)
        posterior_sigma = posterior_information**(-0.5)
        proposal_density = self.tiny(
            num_measurements=0, prior_mean=5.0, prior_sigma=posterior_sigma)

        # Estimate marginals using importance sampling.
        marginals = self.estimate_marginals(
            target=unnormalized_posterior, proposal_density=proposal_density)
        # print(f"True mode: {values.atDiscrete(M(0))}")
        # print(f"P(mode=0; Z) = {marginals[0]}")
        # print(f"P(mode=1; Z) = {marginals[1]}")

        # Check that the estimate is close to the true value.
        self.assertAlmostEqual(marginals[0], 0.23, delta=0.01)
        self.assertAlmostEqual(marginals[1], 0.77, delta=0.01)

        # Convert to factor graph using measurements.
        fg = self.factor_graph_from_bayes_net(bayesNet, values)
        self.assertEqual(fg.size(), 4)

        # Calculate ratio between Bayes net probability and the factor graph:
        expected_ratio = self.calculate_ratio(bayesNet, fg, values)
        # print(f"expected_ratio: {expected_ratio}\n")

        # Check with a number of other samples.
        for i in range(10):
            samples = bayesNet.sample()
            samples.update(measurements)
            ratio = self.calculate_ratio(bayesNet, fg, samples)
            # print(f"Ratio: {ratio}\n")
            if (ratio > 0):
                self.assertAlmostEqual(ratio, expected_ratio)

        # Test elimination.
        ordering = gtsam.Ordering()
        ordering.push_back(X(0))
        ordering.push_back(M(0))
        posterior = fg.eliminateSequential(ordering)

        # Calculate ratio between Bayes net probability and the factor graph:
        expected_ratio = self.calculate_ratio(posterior, fg, values)
        # print(f"expected_ratio: {expected_ratio}\n")

        # Check with a number of other samples.
        for i in range(10):
            samples = posterior.sample()
            samples.insert(measurements)
            ratio = self.calculate_ratio(posterior, fg, samples)
            # print(f"Ratio: {ratio}\n")
            if (ratio > 0):
                self.assertAlmostEqual(ratio, expected_ratio)


if __name__ == "__main__":
    unittest.main()
