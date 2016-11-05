
class CodeGenStrategy(object):
    """
    Defines the strategy wrt how a transformer group is rendered.  This
    is specifically agnostic of the language and instead is responsible
    for transforming/rewriting the TransformerGroup AST into another AST 
    that is more conducive of being emitted via templates so that there
    needs to be less language agnostic work to be done by the template.
    """
    def generate_transformer_ast(self, transformer):
        """
        Generates the AST for a transformer.  Each transformer could specify
        its own vocabulary as to what the nodes in its AST mean.  The primary
        AST for a transformer is the transformer (and its statements) itself.

        Only requirement is that when an AST is provided to a ASTTransformer,
        that it understand the nodes provided to it (otherwise it wont be able
        to transform it).
        """
        pass
