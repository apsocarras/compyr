# Load utility functions
source('R_utils.R')

# Write handler to accept four sets of command line arguments: 
    # The name of the .R file containing the function to test 
    # The function's name
    # Argument key:value pairs (see error message for usage)    
    # A directory of parameters/other R objects to load from .rdata files

help_str <- '
Usage: Rscript profile_R_func.R <R_script_name>.R <R_func_name> -a <positional_args> -k <keyword_args>, -p <parameter_files>

Profile the performance and behavior of any R function via a CLI without modifying the R source code. 
Intended to be run within a Python subprocess; print its output to STDOUT to be captured within subprocess.CompletedProcess. 


Options: 

-h, --help          Show this help message and exit. 
-a, --args          Positional arguments separated by spaces. 
-k, --kwargs        Key-value arguments formatted "<key>=<value>", separated by spaces 
-p, --params        Path to a directory or .rdata file containing other R objects required for your function 
                        - **Warning**: It is bad SWE practice to write a function that relies on global variables undeclared in the function signature
                        for many reasons (e.g. accidental, undetected mutations, lack of portability, lack of dependency injection). Option provided for legacy code.                          

' 
cat(help_str)

profile_R_func <- function() { 

    args <- commandArgs(trailingOnly = TRUE)

    if (length(args) < 2) {
        stop("Must provide .R file w/ function name plus (optional) arguments and (optional) a directory of additional R objects in .rdata files).\n E.g. Rscript profile_function.R my_functions.R my_function x 42 df=\"csv:name,age\nFoo,30\nBar,25\".\nGiven: ", args, "\n",  usage_str)
    }

    r_file <- args[1]
    func_name <- args[2]
    check_file_func(R_file_name=r_file, R_func_name=func_name)

    remaining_args <- paste(args[3:length(args)], collapse=" ") # wrote the while loop as if reamining_args was a string
    
    arg_groups <- group_command_args(remaining_args)

    pos_args <- parse_pos_arg_str(arg_groups['pos_args'])
    kwargs <- parse_kwargs_pairs(arg_groups['kwargs'])
    load_param_files(arg_groups['param_files'])

    # Run and profile function
    func <- get(func_name)
    result_w_profiling <- profiler(func, !!!pos_args, !!!kwargs)

    }

profiler <- function(func, ...) {
#' Actual profiler function 

    # Start memory profiling.
    Rprofmem("memory_profile.log")

    time_info <- system.time({
        output <- do.call(func, list(...))
    })

    # If the result was a DataFrame, parse that back to a CSV string 
    if (is.data.frame(result_w_profiling$output)) { 
        result_w_profiling$output <- paste(capture.output(
            write.csv(result_w_profiling$output, row.names = FALSE)), 
            collapse = "\n")
    }
  
    # Stop memory profiling
    Rprofmem(NULL)

    memory_usage <- sum(as.numeric(readLines("memory_profile.log")))

    unlink("memory_profile.log")

    result <- data.frame(
      output = output, 
      user_time = time_info["user.self"],
      sys_time = time_info["sys.self"],
      elapsed_time = time_info["elapsed"], 
      memory_usage = memory_usage
      )

    return(result)
}

# Run 
profile_R_func()


