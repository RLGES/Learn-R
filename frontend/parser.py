"""
Simple recursive-descent parser for expression language.

Grammar:
    program   -> statement*
    statement -> assignment | if_stmt | while_stmt
    assignment -> IDENT '=' expr NEWLINE
    if_stmt    -> 'if' '(' expr ')' '{' statement* '}' ('else' '{' statement* '}')?
    while_stmt -> 'while' '(' expr ')' '{' statement* '}'
    expr      -> term (('+' | '-') term)*
    term      -> factor (('*') factor)*
    factor    -> NUMBER | IDENT | '(' expr ')'
    comp      -> expr (('<' | '>' | '<=' | '>=' | '==' | '!=') expr)?

Example input:
    a = 5
    if (a < 10) {
        b = a + 3
    }
    while (b > 0) {
        b = b - 1
    }
"""
from typing import List, Optional
from .ast_nodes import Expr, IntLiteral, Variable, BinOp, Assign, Block, If, While


class Token:
    """Represents a lexical token."""
    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value
    
    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


class Lexer:
    """Simple lexer for tokenizing input."""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.current_char = self.text[0] if text else None
    
    def error(self, msg: str = "Invalid character"):
        raise SyntaxError(f"{msg} at position {self.pos}")
    
    def advance(self):
        """Move to next character."""
        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]
    
    def skip_whitespace(self):
        """Skip spaces and tabs (but not newlines)."""
        while self.current_char is not None and self.current_char in ' \t':
            self.advance()
    
    def read_number(self) -> str:
        """Read a number from input."""
        result = ''
        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()
        return result
    
    def read_identifier(self) -> str:
        """Read an identifier (variable name or keyword)."""
        result = ''
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        return result
    
    def peek(self, offset: int = 1) -> Optional[str]:
        """Look ahead at character without consuming."""
        pos = self.pos + offset
        if pos < len(self.text):
            return self.text[pos]
        return None
    
    def get_next_token(self) -> Optional[Token]:
        """Get the next token from input."""
        while self.current_char is not None:
            if self.current_char in ' \t':
                self.skip_whitespace()
                continue
            
            if self.current_char == '\n':
                self.advance()
                return Token('NEWLINE', '\n')
            
            if self.current_char.isdigit():
                return Token('NUMBER', self.read_number())
            
            if self.current_char.isalpha() or self.current_char == '_':
                ident = self.read_identifier()
                # Check for keywords
                if ident == 'if':
                    return Token('IF', ident)
                elif ident == 'else':
                    return Token('ELSE', ident)
                elif ident == 'while':
                    return Token('WHILE', ident)
                else:
                    return Token('IDENT', ident)
            
            if self.current_char == '=':
                # Check for ==
                if self.peek() == '=':
                    self.advance()
                    self.advance()
                    return Token('EQEQ', '==')
                self.advance()
                return Token('EQUALS', '=')
            
            if self.current_char == '!':
                # Check for !=
                if self.peek() == '=':
                    self.advance()
                    self.advance()
                    return Token('NEQ', '!=')
                self.error("Expected '=' after '!'")
            
            if self.current_char == '<':
                # Check for <=
                if self.peek() == '=':
                    self.advance()
                    self.advance()
                    return Token('LTE', '<=')
                self.advance()
                return Token('LT', '<')
            
            if self.current_char == '>':
                # Check for >=
                if self.peek() == '=':
                    self.advance()
                    self.advance()
                    return Token('GTE', '>=')
                self.advance()
                return Token('GT', '>')
            
            if self.current_char == '+':
                self.advance()
                return Token('PLUS', '+')
            
            if self.current_char == '-':
                self.advance()
                return Token('MINUS', '-')
            
            if self.current_char == '*':
                self.advance()
                return Token('MULTIPLY', '*')
            
            if self.current_char == '(':
                self.advance()
                return Token('LPAREN', '(')
            
            if self.current_char == ')':
                self.advance()
                return Token('RPAREN', ')')
            
            if self.current_char == '{':
                self.advance()
                return Token('LBRACE', '{')
            
            if self.current_char == '}':
                self.advance()
                return Token('RBRACE', '}')
            
            self.error(f"Unknown character: {self.current_char!r}")
        
        return Token('EOF', '')


class Parser:
    """Recursive-descent parser for expression language."""
    
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
    
    def error(self, msg: str = "Invalid syntax"):
        raise SyntaxError(f"{msg}, got {self.current_token}")
    
    def eat(self, token_type: str):
        """Consume a token of given type."""
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"Expected {token_type}")
    
    def factor(self) -> Expr:
        """
        Parse a factor: NUMBER | IDENT | '(' expr ')'
        """
        token = self.current_token
        
        if token.type == 'NUMBER':
            self.eat('NUMBER')
            return IntLiteral(int(token.value))
        
        elif token.type == 'IDENT':
            self.eat('IDENT')
            return Variable(token.value)
        
        elif token.type == 'LPAREN':
            self.eat('LPAREN')
            expr = self.expr()
            self.eat('RPAREN')
            return expr
        
        else:
            self.error("Expected number, variable, or '('")
    
    def term(self) -> Expr:
        """
        Parse a term: factor (('*') factor)*
        """
        node = self.factor()
        
        while self.current_token.type == 'MULTIPLY':
            op = self.current_token.value
            self.eat('MULTIPLY')
            node = BinOp(op, node, self.factor())
        
        return node
    
    def expr(self) -> Expr:
        """
        Parse an expression: term (('+' | '-') term)*
        or comparison: expr (('<' | '>' | '<=', '>=' | '==' | '!=') expr)?
        """
        node = self.term()
        
        # Arithmetic operators
        while self.current_token.type in ('PLUS', 'MINUS'):
            op = self.current_token.value
            if self.current_token.type == 'PLUS':
                self.eat('PLUS')
            else:
                self.eat('MINUS')
            node = BinOp(op, node, self.term())
        
        # Comparison operators
        if self.current_token.type in ('LT', 'GT', 'LTE', 'GTE', 'EQEQ', 'NEQ'):
            op = self.current_token.value
            self.eat(self.current_token.type)
            right = self.term()
            # Continue with arithmetic on right side
            while self.current_token.type in ('PLUS', 'MINUS'):
                op2 = self.current_token.value
                if self.current_token.type == 'PLUS':
                    self.eat('PLUS')
                else:
                    self.eat('MINUS')
                right = BinOp(op2, right, self.term())
            node = BinOp(op, node, right)
        
        return node
    
    def statement(self):
        """
        Parse a statement: assignment | if_stmt | while_stmt
        """
        if self.current_token.type == 'IF':
            return self.if_statement()
        elif self.current_token.type == 'WHILE':
            return self.while_statement()
        elif self.current_token.type == 'IDENT':
            return self.assignment()
        else:
            self.error("Expected statement")
    
    def assignment(self) -> Assign:
        """
        Parse an assignment: IDENT '=' expr
        """
        if self.current_token.type != 'IDENT':
            self.error("Expected variable name")
        
        var_name = self.current_token.value
        self.eat('IDENT')
        self.eat('EQUALS')
        expr = self.expr()
        
        return Assign(var_name, expr)
    
    def if_statement(self) -> If:
        """
        Parse if statement: 'if' '(' expr ')' '{' statement* '}' ('else' '{' statement* '}')?
        """
        self.eat('IF')
        self.eat('LPAREN')
        condition = self.expr()
        self.eat('RPAREN')
        self.eat('LBRACE')
        
        # Parse then block
        then_statements = []
        while self.current_token.type != 'RBRACE':
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
                continue
            then_statements.append(self.statement())
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
        self.eat('RBRACE')
        
        then_block = Block(then_statements)
        
        # Optional else clause
        else_block = None
        if self.current_token.type == 'ELSE':
            self.eat('ELSE')
            self.eat('LBRACE')
            else_statements = []
            while self.current_token.type != 'RBRACE':
                if self.current_token.type == 'NEWLINE':
                    self.eat('NEWLINE')
                    continue
                else_statements.append(self.statement())
                if self.current_token.type == 'NEWLINE':
                    self.eat('NEWLINE')
            self.eat('RBRACE')
            else_block = Block(else_statements)
        
        return If(condition, then_block, else_block)
    
    def while_statement(self) -> While:
        """
        Parse while statement: 'while' '(' expr ')' '{' statement* '}'
        """
        self.eat('WHILE')
        self.eat('LPAREN')
        condition = self.expr()
        self.eat('RPAREN')
        self.eat('LBRACE')
        
        # Parse body
        body_statements = []
        while self.current_token.type != 'RBRACE':
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
                continue
            body_statements.append(self.statement())
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
        self.eat('RBRACE')
        
        body = Block(body_statements)
        return While(condition, body)
    
    def program(self) -> Block:
        """
        Parse a program: statement*
        """
        statements = []
        
        # Skip leading newlines
        while self.current_token.type == 'NEWLINE':
            self.eat('NEWLINE')
        
        while self.current_token.type != 'EOF':
            stmt = self.statement()
            statements.append(stmt)
            
            # Consume newline or check for EOF
            if self.current_token.type == 'NEWLINE':
                self.eat('NEWLINE')
            elif self.current_token.type != 'EOF':
                self.error("Expected newline or end of input")
        
        return Block(statements)


def parse(source_code: str) -> Block:
    """
    Parse source code into an AST.
    
    Args:
        source_code: Source code string (e.g., "a = 5\nb = a + 3")
    
    Returns:
        Block AST representing the program
    
    Example:
        >>> ast = parse("a = 5\nb = a + 3")
        >>> print(ast)
        a = 5
        b = (a + 3)
    """
    lexer = Lexer(source_code)
    parser = Parser(lexer)
    return parser.program()
