check_file_func <- function(R_file_name, R_func_name, env) { 

    if (missing(env)) {
        env_to_check <- new.env() 
    } else { 
        env_to_check <- env 
    }
    source(R_file_name, local = env_to_check)

    if (!exists(R_func_name, envir = env_to_check)) {
        func_list <- env_to_check[sapply(all_functions, function(x) is.function(get(x)))]
        stop(paste0("Function '", R_func_name, "' does not exist in the file '", R_file_name, "'.\n",
                    "Functions currently available in the R environment are: ", paste(func_list, collapse = ", ")))    
        return(FALSE)
    }
    message(paste0("Function '", R_func_name, "' exists in the file '", R_file_name, "'."))
    return(TRUE)
}

if (interactive() == FALSE) {

    args <- commandArgs(trailingOnly = TRUE)

    if (length(args) < 2) {
        stop("Usage: Rscript check_file_func.R <R_file_name> <R_func_name>")
    }

    R_file_name <- args[1]
    R_func_name <- args[2]

    result <- check_file_func(R_file_name, R_func_name)

    print(result)

}