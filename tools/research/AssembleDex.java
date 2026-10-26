import com.android.tools.smali.smali.Smali;
import com.android.tools.smali.smali.SmaliOptions;

public class AssembleDex {
    public static void main(String[] args) throws Exception {
        SmaliOptions options = new SmaliOptions();
        options.apiLevel = 24;
        options.jobs = 4;
        options.outputDexFile = args[1];
        options.verboseErrors = true;
        if (!Smali.assemble(options, args[0])) throw new IllegalStateException("Assembly failed");
    }
}
