/**
 * @file DummyFactor.h
 *
 * @brief A simple factor that can be used to trick gtsam solvers into believing a graph is connected.
 * 
 * @date Sep 10, 2012
 * @author Alex Cunningham
 */

#pragma once

#include <gtsam/nonlinear/NonlinearFactor.h>

namespace gtsam {

class DummyFactor : public NonlinearFactor {
protected:

  // Store the dimensions of the variables and the dimension of the full system
  std::vector<size_t> dims_;
  size_t rowDim_; ///< choose dimension for the rows

public:

  /** Default constructor: don't use directly */
  DummyFactor() : rowDim_(1) { }

  /** standard binary constructor */
  DummyFactor(const Key& key1, size_t dim1, const Key& key2, size_t dim2);

  virtual ~DummyFactor() {}

  // testable

  /** print */
  virtual void print(const std::string& s = "", const KeyFormatter& keyFormatter = DefaultKeyFormatter) const;

  /** Check if two factors are equal */
  virtual bool equals(const NonlinearFactor& f, double tol = 1e-9) const;

  // access

  const std::vector<size_t>& dims() const { return dims_; }

  // factor interface

  /**
   * Calculate the error of the factor - zero for dummy factors
   */
  virtual double error(const Values& c) const { return 0.0; }

  /** get the dimension of the factor (number of rows on linearization) */
  virtual size_t dim() const { return rowDim_; }

  /** linearize to a GaussianFactor */
  virtual boost::shared_ptr<GaussianFactor>
  linearize(const Values& c, const Ordering& ordering) const;

  /**
   * Creates a shared_ptr clone of the factor - needs to be specialized to allow
   * for subclasses
   *
   * By default, throws exception if subclass does not implement the function.
   */
  virtual NonlinearFactor::shared_ptr clone() const {
    return boost::static_pointer_cast<NonlinearFactor>(
        NonlinearFactor::shared_ptr(new DummyFactor(*this)));
  }

};

} // \namespace gtsam




