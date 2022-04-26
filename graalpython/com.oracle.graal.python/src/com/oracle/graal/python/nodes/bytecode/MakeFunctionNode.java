package com.oracle.graal.python.nodes.bytecode;

import static com.oracle.graal.python.nodes.SpecialAttributeNames.__ANNOTATIONS__;

import com.oracle.graal.python.PythonLanguage;
import com.oracle.graal.python.builtins.objects.cell.PCell;
import com.oracle.graal.python.builtins.objects.code.PCode;
import com.oracle.graal.python.builtins.objects.function.PFunction;
import com.oracle.graal.python.builtins.objects.function.PKeyword;
import com.oracle.graal.python.builtins.objects.function.Signature;
import com.oracle.graal.python.builtins.objects.object.PythonObject;
import com.oracle.graal.python.compiler.CodeUnit;
import com.oracle.graal.python.nodes.PBytecodeRootNode;
import com.oracle.graal.python.nodes.PNodeWithContext;
import com.oracle.graal.python.nodes.generator.PBytecodeGeneratorFunctionRootNode;
import com.oracle.graal.python.runtime.object.PythonObjectFactory;
import com.oracle.truffle.api.RootCallTarget;
import com.oracle.truffle.api.dsl.Cached;
import com.oracle.truffle.api.dsl.Specialization;
import com.oracle.truffle.api.frame.Frame;
import com.oracle.truffle.api.library.CachedLibrary;
import com.oracle.truffle.api.object.DynamicObjectLibrary;
import com.oracle.truffle.api.source.Source;

public abstract class MakeFunctionNode extends PNodeWithContext {
    private final RootCallTarget callTarget;
    private final CodeUnit code;
    private final Signature signature;
    private final PCode cachedCode;

    public abstract int execute(Object globals, int initialStackTop, Frame localFrame, int flags);

    public MakeFunctionNode(RootCallTarget callTarget, CodeUnit code, Signature signature, PCode cachedCode) {
        this.callTarget = callTarget;
        this.code = code;
        this.signature = signature;
        this.cachedCode = cachedCode;
    }

    @Specialization
    int makeFunction(Object globals, int initialStackTop, Frame localFrame, int flags,
                    @Cached PythonObjectFactory factory,
                    @CachedLibrary(limit = "1") DynamicObjectLibrary dylib) {
        // TODO __doc__
        int stackTop = initialStackTop;

        PCell[] closure = null;
        Object annotations = null;
        PKeyword[] kwdefaults = null;
        Object[] defaults = null;

        if ((flags & CodeUnit.HAS_CLOSURE) != 0) {
            closure = (PCell[]) localFrame.getObject(stackTop);
            localFrame.setObject(stackTop--, null);
        }
        if ((flags & CodeUnit.HAS_ANNOTATIONS) != 0) {
            annotations = localFrame.getObject(stackTop);
            localFrame.setObject(stackTop--, null);
        }
        if ((flags & CodeUnit.HAS_KWONLY_DEFAULTS) != 0) {
            kwdefaults = (PKeyword[]) localFrame.getObject(stackTop);
            localFrame.setObject(stackTop--, null);
        }
        if ((flags & CodeUnit.HAS_DEFAULTS) != 0) {
            defaults = (Object[]) localFrame.getObject(stackTop);
            localFrame.setObject(stackTop--, null);
        }
        PCode codeObj = cachedCode;
        if (codeObj == null) {
            // Multi-context mode
            codeObj = createCode(factory, code, callTarget, signature);
        }
        PFunction function = factory.createFunction(code.name, code.qualname, codeObj, (PythonObject) globals, defaults, kwdefaults, closure);
        if (annotations != null) {
            dylib.put(function, __ANNOTATIONS__, annotations);
        }
        localFrame.setObject(++stackTop, function);
        return stackTop;
    }

    private static PCode createCode(PythonObjectFactory factory, CodeUnit code, RootCallTarget callTarget, Signature signature) {
        return factory.createCode(callTarget, signature, code.varnames.length, code.stacksize, code.flags, code.constants, code.names,
                        code.varnames, code.freevars, code.cellvars, null, code.name, code.startOffset, code.srcOffsetTable);
    }

    public static MakeFunctionNode create(PythonLanguage language, CodeUnit code, Source source) {
        RootCallTarget callTarget;
        PBytecodeRootNode bytecodeRootNode = new PBytecodeRootNode(language, code, source);
        if (code.isGeneratorOrCoroutine()) {
            // TODO what should the frameDescriptor be? does it matter?
            callTarget = new PBytecodeGeneratorFunctionRootNode(language, bytecodeRootNode.getFrameDescriptor(), bytecodeRootNode, code.name).getCallTarget();
        } else {
            callTarget = bytecodeRootNode.getCallTarget();
        }
        PCode cachedCode = null;
        if (language.isSingleContext()) {
            cachedCode = createCode(PythonObjectFactory.getUncached(), code, callTarget, bytecodeRootNode.getSignature());
        }
        return MakeFunctionNodeGen.create(callTarget, code, bytecodeRootNode.getSignature(), cachedCode);
    }
}
