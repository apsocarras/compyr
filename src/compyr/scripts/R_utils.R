
group_command_args <- function(args) {
#' Group command line arguments into positional, key:value pairs, and param files based on option flags 
  
    result <- list('pos_args' = NULL, 'kwargs' = NULL, 'param_files' = NULL)
  
    known_options <- '(-h|--help)|(-a|--args)|(-k|--kwargs)|(-p|--params)'
    
    # I wrote the while loop as if commandArgs() returned a string -- didn't want to refactor 
    if (!is.vector(args) || !is.list(args)) {
        arg_str <- paste(args[3:length(args)], collapse=" ") 
    } else if (is.character(args)) { 
        arg_str <- args 
    } else { 
        stop(paste0("`args` must be a vector, list, or string (given: ", typeof(args), ")"))
    }

    cur_match <- regexpr(pattern = known_options, 
                           arg_str[i:nchar(arg_str)]) # index vector, match.length attribute

    while(cur_match[1] != -1) {
      cur_opt <- substring(arg_str, cur_match[1], cur_match[1] + attr(cur_match, "match.length"))
    
      if (cur_opt %in% c('-h', '--help')) {
        message(help_str)
        return (NULL)

      } else { 
        vals_start <- cur_match[1] + attr(cur_match, "match.length") + 1

        next_match <- regexpr(known_options, substring(arg_str, vals_start, nchar(arg_str)))

        vals_end <- if (next_match[1] == -1) {
            nchar(arg_str)
          } else {
            vals_start + next_match[1] - 1  # Adjust index for next match
          }        
          
          cur_opt_values <- substring(arg_str, vals_start, vals_end)
    
          if (cur_opt %in% c('-a', '--args')) {
            result['pos_args'] <- cur_opt_values

          } else if (cur_opt %in% c('-k', '--kwargs')) {
            result['kwargs'] <- cur_opt_values 
            
          } else if (cur_opt %in% c('-p', '--params')) {
            result['param_files'] <- cur_opt_values
          }

        cur_match <- next_match
      }
    }

    return (result)

}

parse_pos_arg_str <- function(arg_str) {
    pos_arg_list <- strsplit(arg_str, split = ",")
    for (i in seq_along(pos_arg_list)) {
        if (is.character(pos_arg_list[i])) {
            # Attempt to parse into DataFrame 
            pos_arg_list[i] <- parse_str_to_df(pos_arg_list[i])
        }
    }
    return (pos_arg_list)
}

parse_kwargs_pairs <- function(kwarg_pairs) {
    key_value_list <- lapply(kwarg_pairs, function(pair) {
        pair_cleaned <- gsub('"', '', pair)  # Remove quotes
        key_value <- strsplit(pair_cleaned, split = "=")[[1]]
        # Call parse_str_to_df on value argument
        if (is.character(key_value[2])) {
            key <- key_value[1]
            value <- parse_str_to_df(key_value[2])
        }
        return(list(key = key, value = value))
    })
    return (key_value_list)
}

load_param_files <- function(dir_name, file_name) {
#' Load a directory of .rdata files containing global parameters for your function 
    if (!missing(dir_name)) {
        files <- list.files(dir_name)
            for (file in files) {
                if (tolower(tools::file_ext(file)) == 'rdata') {
                    load(file)        
                }
            }
    } else {
        if (tolower(tools::file_ext(file)) == 'rdata') {
            load(file)
        }
    }
}

parse_str_to_df <- function(string) {
#' Attermpt to parse a str argument to a DataFrame based on csv: prefix or file extension suffix. 
#' Returns <string> if netiher applies.
  if (startsWith(string, 'csv:')) {
    csv_data <- sub('csv:', '', string)
    con <- textConnection(substring(csv_data, nchar('csv:') + 1, nchar(string)))
    df <- read.csv(con, stringsAsFactors = FALSE)
    close(con)
    return(df)
  
    } else if (endsWith(string, ".csv")) {
        df <- read.csv(string)
        return(df)
    } else if (endsWith(string, ".parquet")) {
        stop('Package currently does not support .parquet files (to avoid external dependencies)')
    } else {
        return(string)
    }
}

