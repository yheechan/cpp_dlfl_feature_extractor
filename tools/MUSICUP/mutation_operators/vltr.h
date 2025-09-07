#ifndef MUSIC_VLTR_H_
#define MUSIC_VLTR_H_

#include "expr_mutant_operator.h"

class VLTR : public ExprMutantOperator
{
public:
	VLTR(const std::string name = "VLTR")
		: ExprMutantOperator(name), num_partitions(10)
	{}

	virtual bool ValidateDomain(const std::set<std::string> &domain);
	virtual bool ValidateRange(const std::set<std::string> &range);
	virtual void setRange(std::set<std::string> &range);
	
	// Return True if the mutant operator can mutate this expression
	virtual bool IsMutationTarget(clang::Expr *e, MusicContext *context);

	virtual void Mutate(clang::Expr *e, MusicContext *context);
	
private:
	std::set<int> partitions;
  int num_partitions;

	void GetRange(clang::Expr *e, MusicContext *context, VarDeclList *range);
	bool HandleRangePartition(std::string option);
  void ApplyRangePartition(std::vector<std::string> *range);
};

#endif	// MUSIC_VLTR_H_