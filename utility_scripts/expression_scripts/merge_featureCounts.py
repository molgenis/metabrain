# Merge FeatureCount count files (counts per sample) to matrix with rows genes, columns samples
# NOTE: Needs Python version 3.5+
import glob
import argparse
import gzip
import sys
parser = argparse.ArgumentParser(description='Merge multiple FeatureCount count files into a matrix. Uses featureCount_directory in which files are located to make matrix name')
parser.add_argument('featureCount_directory', help='featureCount_directory which contains gzipped feature count .txt.gz files')
parser.add_argument('out_prefix', help='prefix of outfile')

args = parser.parse_args()
set_of_features = set([])
featureCount_directory = args.featureCount_directory
list_of_features = []
if featureCount_directory.endswith('/'):
    feature_type = featureCount_directory.split('/')[-2]
else:
    feature_type = featureCount_directory.split('/')[-1]

print(feature_type, featureCount_directory)
sys.stdout.flush()

def parse_gtf(gtf, feature_type):
    print(feature_type+': parse GTF file to get feature name')
    sys.stdout.flush()
    feature_name = feature_type.split('.')[0]
    feature_info = {}
    with open(gtf) as input_file:
        for line in input_file:
            if line.startswith('#'):
                continue
            line = line.strip().split('\t')
            feature = line[2]
            if feature != feature_name:
                continue
            chr = line[0]
            start = line[3]
            end = line[4]
            info = line[8]
            if feature_name+'_id "' not in info:
                print(line)
                raise RuntimeError(feature_name+'_id " not in info')
            id = info.split(feature_name+'_id "')[1].split('"')[0]
            if chr+start+end in feature_info:
                # add name of overlapping transcripts
                feature_info[chr+start+end] += '_'+id
            else:
                feature_info[chr+start+end] = id
    return(feature_info)

feature_info = None
prev_line = None
with open(args.out_prefix+feature_type+'.txt','w') as out:
    x = 0
    out.write('-')
    for f in glob.iglob(featureCount_directory+'/**/*txt.gz', recursive=True):
        # open the first file to get a list of features

        if x == 0:
            print(feature_type+': read first file to get a list of features')
            sys.stdout.flush()
            with gzip.open(f) as input_file:
                for line in input_file:
                    line = line.decode('utf-8')
                    if line.startswith('#'):
                        if 'metaExon' not in feature_type:
                            gtf = line.split('-a" "')[1].split('"')[0]
                            feature_info = parse_gtf(gtf, feature_type)
                        continue
                    if line.startswith('Geneid'):
                        continue
                    line = line.strip().split('\t')
                    chr = line[1]
                    if not chr.startswith('chr'):
                        continue
                    list_of_features.append(line[0])
                    if 'metaExon' not in feature_type:
                        out.write('\t'+feature_info[line[1]+line[2]+line[3]])
                    else:
                        out.write('\t'+line[0])
            out.write('\n')
            print(feature_type+': Done')
            sys.stdout.flush()

        x += 1
        if x % 100 == 0:
            print(feature_type+': '+str(x))
            sys.stdout.flush()
        # sample_name of the sample is everything before . of the filename
        sample_name = f.split('/')[-1].split('.')[0]
        out.write(sample_name)
        with gzip.open(f) as input_file:
            input_file.readline()
            y = 0
            for line in input_file:
                if line == prev_line:
                    # some lines are identical because of overlapping transcript, if so, skip
                    y += 1
                    continue
                prev_line = line
                line = line.decode('utf-8')
                if line.startswith('#') or line.startswith('Geneid'):
                    continue
                line = line.strip().split('\t')
                chr = line[1]
                if not chr.startswith('chr'):
                    continue
                if line[0] != list_of_features[y]:
                    raise RuntimeError('feature not the same. Current: '+line[0]+'. Original: '+list_of_features[y]+'. Index: '+str(y))
                feature =  line[0]
                count = line[6]
                out.write('\t'+count)
                y += 1
        out.write('\n')

print(feature_type+': Done')
