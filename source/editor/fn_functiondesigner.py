from scipy.optimize import curve_fit
import numpy as np

# Before using this, "function" HAS to be sanitised to avoid any exploits.

def CalcParsValues(xdata, ydata, independent, funcpars, function):
    """
    Performs curve fitting and returns optimised parameters
    and covariances for each parameter

    Arguments:
        xdata -> list of numbers (float); independent variable,
                 e.g. compound concentration
        ydata -> list of numbers (float); dependent (experimenta)
                 data, e.g. fluorescence, normalised response, etc.
        funcpars -> list strings; parameters of the function
        function -> string; function of the curve which is to be
                    fitted to the experimental data.
    """

    str_Funcpars = ListToString(funcpars)

    # Define the function with exec()
    exec("def TheFunction(" + independent + ", " + str_Funcpars
         + "):\n    return " + function )

    # call the function with eval()
    lst_Parameters, lst_Covariance = eval("curve_fit(TheFunction, xdata, ydata)")

    return list(lst_Parameters)

def ListToString(input):
    """
    Turns list of parameters into string.
    """
    output = str(input[0])
    if len(input) > 1:
        for i in range(len(input)-1):
            output = output + "," + str(input[i+1])
    
    return output

def CalculateCurve(xdata, parvalues, independent, funcpars, function):
    """
    Calculates values for fitted curve based on function and parameters.
    """
    str_Funcpars = ListToString(funcpars)
    str_ParValues = ListToString(parvalues)

    # Define the function with exec()
    exec("def TheFunction(" + independent + ", " + str_Funcpars
         + "):\n    return " + function )
    fit = []
    for datapoint in xdata:
        fit.append(eval("TheFunction(datapoint, " + str_ParValues + ")"))
    return fit

def FunctionToList(funcstring):
    """
    Turns a string into a list of operators, parentheses, 
    parameters and constants
    """

    operators = ["/", "*", "+", "-"]
    parentheses = ["(",")"]

    output = []
    ele = ""
    funlen = len(funcstring)

    for char in range(funlen):
        if not funcstring[char] in operators + parentheses + [" ","$"]:
            # Character is likely part of a constant or parameter
            ele += funcstring[char]
            if char == funlen - 1:
                # We're at the end, nothing else needs to be done
                output.append(ele)
                break
        else:
            if len(ele) > 0:
                output.append(ele)
            if (funcstring[char] == " " and char == funlen -1) or (
                funcstring[char] in operators + parentheses):
                ele = funcstring[char]
                output.append(ele)
            ele = "" # reset

    #print("Function text:")
    #print(funcstring + "|")
    #print("Function list:")
    #print(output)
    return output

def Formatting(funclist, independent, operators, parameters):
    format = []
    for ele in funclist:
        if ele in operators or ele.isnumeric() == True:
            format.append("default")
        elif ele == independent:
            format.append("independent")
        elif ele in parameters:
            format.append("parameter")
        else:
            format.append("underlined")
    return format

def AddNumpyToFunction(function):
    lst_Function = FunctionToList(function)
    str_Function = ""

    lst_Numpy = ["exp","sqrt","sin","cos","log"]

    for ele in lst_Function:
        if ele in lst_Numpy:
            str_Function += "np." + ele
        else:
            str_Function += ele

    return str_Function

def FunctionToListSingleSpace(function):
    """
    Turns a string into a list of operators, parentheses, 
    parameters and constants
    """

    specialchars = ["/", "*", "+", "-", "(", ")"]

    output = []
    ele = ""

    for char in range(len(function)):
        # Character is likely part of a constant or parameter
        if not function[char] in specialchars and not function[char] == " ":
            ele += function[char]
        else:
            if len(ele) > 0:
                output.append(ele)
            if function[char] in specialchars:
                output.append(function[char])
            ele = "" # reset
            # Char is single character operator or parenthesis

    return output

def ReduceSpaces(string):
    bol_AllSpaces = True
    string = "Fnord"
    if not string.count(" ") == len(string):
        bol_AllSpaces = False

    return None

def VerifyFunction(str_Function, lst_EnteredPars, independent):
    """"
    Verifies whether a function can work by testing for certain criteria.
    """

    # Lists for testing, i.e. signle-character operators, multi-character
    # operators. 
    lst_SCOperators = ["/", "*", "+", "-"]
    lst_MCOperators = ["sqrt", "exp", "log", "ln", "**"]

    # Check the string is longer than 0
    if not len(str_Function) > 0:
        print("Function string is empty")
        return False

    # Do we have the same number of opening and closing parentheses?
    # This does not guarantee that he function is OK, but if the numbers don't
    # match, it is definitely NOT OK.
    int_Open = str_Function.count("(")
    int_Close = str_Function.count(")")
    if not int_Open == int_Close:
        print("Number of opening and closing parentheses don't match")
        return False

    # Turn function into list
    lst_Function = FunctionToList(str_Function)

    # Is the independent variable in the function
    if not independent in lst_Function:
        print("Independent variable is not in function")
        return False

    # Are all opening and closing parentheses actually matched?
    if MatchingParentheses(lst_Function) == False:
        print("Parentheses are not balanced")
        return False

    # First character cannot be operator
    if lst_Function[0] in lst_SCOperators:
        print("First character of function is an operator")
        return False
    # last character cannot be operator
    if lst_Function[-1] in lst_SCOperators:
        print("Last character of function is an operator")
        return False

    # Check if all operators have operands
    if OperatorsMatched(function = lst_Function,
                        operators = lst_SCOperators + lst_MCOperators) == False:
        print("Not all operators are matched with an operand")
        return False

    # Are all parameters in the function in the list of parameters
    lst_NotInList = []
    lst_FuncPars = ExtractParameters(function = lst_Function,
                                     ignorechars = lst_SCOperators + ["(",")", " "],
                                     ignorewords = lst_MCOperators,
                                     independent = independent)
    print("Parameters identified:")
    print(lst_FuncPars)
    for par in lst_FuncPars:
        if not par in lst_EnteredPars:
            # If we can turn the par in question into a floating point number,
            # it is a constant. If we can't, it's a parameter
            try:
                constant = float(par)
            except:
                lst_NotInList.append(par)
    if len(lst_NotInList) > 0:
        print("At least one parameter was not in the list. Please check your spelling.")
        print(lst_NotInList)
        return False

    # If we get to this point, all is well
    return True

def OperatorsMatched(function, operators):
    """
    Checks if all operators are matched with an operand
    """
    for ele in range(len(function)):
        if function[ele] in operators:
            if ele > 0:
                if function[ele - 1] == "(":
                    print("We have an operator without operand: " + function[ele])
                    return False
            elif ele < len(function) -1:
                if function[ele + 1] == ")":
                    print("We have an operator without operand: " + function[ele])
                    return False

    # If we get to this point, all is well
    return True


def ExtractParameters(function, ignorechars, ignorewords, independent):
    """
    Extracts all parameters from the function string
    """
    pars = []
    
    for elem in function:
        if not elem in ignorechars and not elem in ignorewords and not elem == independent:
            pars.append(elem)
    
    return pars

def MatchingParentheses(function):
    """
    Tests if all parentheses are closed again.
    """

    # Pseudocode first:
    # If character is open parenthesis:
    #   add character to list.
    # if character is close parenthesis:
    #   if len(list) > 0 and last element is an opening parenthesis:
    #       remove last item from list
    #   else:
    #       closed parenthesis without previous open one!
    # if len(list) > 0:
    #   nor all parentheses have matching partner
    # else:
    #   all parentheses have matching partner
    parentheses = []
    for char in function:
        if char == "(":
            parentheses.append(char)
        elif char == ")":
            if len(parentheses) > 0 and parentheses[-1] == "(":
                parentheses.pop()
            else:
                return False
    if len(parentheses) > 0:
        return False
    else:
        return True




