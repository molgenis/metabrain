# This script runs 6th step to making GeneNetwork: Make the correlation matrix

set -e
set -u

project_dir=
outfile=
config_templates=
github_dir=
expression_file=
threads=
mem=
qos=
main(){
    module load Java/1.8.0_144-unlimited_JCE
    parse_commandline "$@"

    rsync -vP $config_templates/6_CorrelationMatrix.json $project_dir/configs/

    sed -i "s;REPLACEEXPRFILE;$expression_file;" $project_dir/configs/6_CorrelationMatrix.json
    sed -i "s;REPLACEOUTFILE;$outfile;" $project_dir/configs/6_CorrelationMatrix.json
    sed -i "s;REPLACETHREADS;$threads;" $project_dir/configs/6_CorrelationMatrix.json
    mkdir -p $(dirname $outfile)

    echo "Starting sbatch with:"
    echo "#!/bin/bash
#SBATCH --job-name=correlation
#SBATCH --output=$(dirname $outfile)/correlation.out
#SBATCH --error=$(dirname $outfile)/correlation.err
#SBATCH --time=05:59:59
#SBATCH --cpus-per-task $threads
#SBATCH --mem ${mem}b
#SBATCH --nodes 1
#SBATCH --qos=$qos

ml Java;
java -Xmx$mem -Xms$mem -jar $github_dir/RunV13.jar $project_dir/configs/6_CorrelationMatrix.json

if [ $? -eq 0 ];
then
    echo "success!"
    touch $(dirname $outfile)/correlation.finished
else
    echo "error!"
    exit 1;
fi

" > $(dirname $outfile)/correlation.sh

    echo "start sbatch with:"
    echo "sbatch $(dirname $outfile)/correlation.sh"
    sbatch $(dirname $outfile)/correlation.sh

    echo "sleep 10 minutes before checking if correlation is done"
    sleep 600
    while [ ! -f $(dirname $outfile)/correlation.finished ]
    do
      echo "$(dirname $outfile)/correlation.finished does not exist yet"
      echo "tail of the .out and .err file of the job:"
      tail $(dirname $outfile)/correlation.out
      tail $(dirname $outfile)/correlation.err

      echo "sleep 2 minutes before checking again"
      sleep 120
    done

    if [ ! -f $outfile ];
    then
        echo "$outfile not made!"
        exit 1;
    fi
    gzip $outfile
}

usage(){
    # print the usage of the programme
    programname=$0
    echo "usage: $programname -e expression_file -p project_directory -o output_dir -j jar_dir -t threads -mem memory -qos qos"
    echo "  -e      Expression file to remove duplciates from"
    echo "  -p      Base of the project_dir where config files will be written"
    echo "  -o      Output file that will be written"
    echo "  -c      Dir with configuration template files"
    echo "  -j      Location of V13 jar file"
    echo "  -t      Number of threads"
    echo "  -h      display help"
    exit 1
}

parse_commandline(){
    # Check to see if at least one argument is given
    if [ $# -eq 0 ]
    then
        echo "ERROR: No arguments supplied"
        usage
        exit 1;
    fi

    while [[ $# -ge 1 ]]; do
        case $1 in
            -p | --project_dir )        shift
                                        project_dir=$1
                                        ;;
            -e | --expression_file )    shift
                                        expression_file=$1
                                        ;;
            -o | --outfile )            shift
                                        outfile=$1
                                        ;;
            -c | --config_templates )   shift
                                        config_templates=$1
                                        ;;
            -t | --threads )            shift
                                        threads=$1
                                        ;;
            -g | --github_dir )         shift
                                        github_dir=$1
                                        ;;
            -m | --mem )                shift
                                        mem=$1
                                        ;;
            -q | --qos )                shift
                                        qos=$1
                                        ;;
            -h | --help )               usage
                                        exit
                                        ;;
            * )                         echo "ERROR: Undexpected argument: $1"
                                        usage
                                        exit 1
        esac
        shift
    done

    # if -z tests if variable is empty. Make sure the relevant variables are set
    if [ -z "$project_dir" ];
    then
        echo "ERROR: -p/--project_dir not set!"
        usage
        exit 1;
    fi
    if [ -z "$expression_file" ];
    then
        echo "ERROR: -e/--expression_file not set!"
        usage
        exit 1;
    fi
    if [ -z "$outfile" ];
    then
        echo "ERROR: -o/--outfile not set!"
        usage
        exit 1;
    fi
    if [ -z "$github_dir" ];
    then
        echo "ERROR: -g/--github_dir not set!"
        usage
        exit 1;
    fi
    if [ -z "$threads" ];
    then
        echo "ERROR: -t/--threads not set!"
        usage
        exit 1;
    fi
    if [ -z "$config_templates" ];
    then
        echo "ERROR: -c/--config_templates not set!"
        usage
        exit 1;
    fi
    if [ -z "$mem" ];
    then
        echo "ERROR: -m/--mem not set!"
        usage
        exit 1;
    fi
    if [ -z "$qos" ];
    then
        echo "ERROR: -q/--qos not set!"
        usage
        exit 1;
    fi
}

# [[ ${BASH_SOURCE[0]} = "$0" ]] -> main does not run when this script is sourced
# main "$@" -> Send the arguments to the main function (this way project flow can be at top)
# exit -> safeguard against the file being modified while it is interpreted
[[ ${BASH_SOURCE[0]} = "$0" ]] && main "$@"; exit;






